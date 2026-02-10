#!/usr/bin/env python3
"""
Garmin 全接口分类型拉取工具。

默认行为:
- 按 docs/python-garminconnect-pull-api-detailed.md 中接口执行
- 按文档分类输出到 garmin_report_<year>/data/
- 默认中国区登录、默认覆盖旧分类数据、默认包含 download_* 接口
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable


API_DOC_DEFAULT = Path("docs/python-garminconnect-pull-api-detailed.md")

SECTION_SLUG_MAP = {
    "User & Profile": "user_profile",
    "Daily Health & Activity": "daily_health_activity",
    "Advanced Health Metrics": "advanced_health_metrics",
    "Historical Data & Trends": "historical_trends",
    "Activities & Workouts": "activities_workouts",
    "Body Composition & Weight": "body_composition_weight",
    "Goals & Achievements": "goals_achievements",
    "Device & Technical": "device_technical",
    "Gear & Equipment": "gear_equipment",
    "Hydration & Wellness": "hydration_wellness",
    "Training Plans": "training_plans",
}

ID_PARAM_TO_SEED_KEY = {
    "activity_id": "activity_ids",
    "workout_id": "workout_ids",
    "scheduled_workout_id": "scheduled_workout_ids",
    "device_id": "device_ids",
    "userProfileNumber": "user_profile_numbers",
    "gearUUID": "gear_uuids",
    "plan_id": "plan_ids",
}

SPECIAL_METHODS = {
    "get_lactate_threshold",
    "get_goals",
    "get_race_predictions",
    "get_progress_summary_between_dates",
}

# Dedup policy: these methods are known duplicates and can be skipped.
EXCLUDED_METHODS = {
    "get_stats",
    "get_stress_data",
    "get_activities_by_date",
}


def parse_api_reference(doc_path: Path) -> list[dict[str, str]]:
    """Parse markdown API doc and return method specs in document order."""
    if not doc_path.exists():
        raise FileNotFoundError(f"API 文档不存在: {doc_path}")

    methods: list[dict[str, str]] = []
    current_section = ""
    current_slug = ""

    section_re = re.compile(r"^##\s+(.+?)(?:\s+\(\d+\))?\s*$")
    method_re = re.compile(r"^###\s+`([^`]+)`\s*$")

    for line in doc_path.read_text(encoding="utf-8").splitlines():
        section_match = section_re.match(line)
        if section_match:
            raw = section_match.group(1).strip()
            if raw in SECTION_SLUG_MAP:
                current_section = raw
                current_slug = SECTION_SLUG_MAP[raw]
            else:
                current_section = ""
                current_slug = ""
            continue

        method_match = method_re.match(line)
        if not method_match or not current_section:
            continue

        signature = method_match.group(1).strip()
        method_name = signature.split("(", 1)[0].strip()
        methods.append(
            {
                "section": current_section,
                "section_slug": current_slug,
                "method": method_name,
                "signature": signature,
            }
        )

    return methods


def parse_signature_params(signature: str) -> list[str]:
    if "(" not in signature or ")" not in signature:
        return []
    inside = signature.split("(", 1)[1].rsplit(")", 1)[0].strip()
    if not inside:
        return []

    params: list[str] = []
    for part in inside.split(","):
        token = part.strip()
        if not token:
            continue
        name = token.split("=", 1)[0].strip()
        if name:
            params.append(name)
    return params


def classify_call_type(method_name: str, signature: str) -> str:
    params = parse_signature_params(signature)
    params_set = set(params)

    if method_name.startswith("download_"):
        return "download"
    if method_name in SPECIAL_METHODS:
        return "special"
    if not params:
        return "noarg"
    if method_name.startswith("get_weekly_") or "weeks" in params_set:
        return "weekly"
    if "cdate" in params_set or "fordate" in params_set:
        return "daily"
    if "start" in params_set and "limit" in params_set:
        return "paged"
    if "startdate" in params_set or "enddate" in params_set or "start_date" in params_set or "end_date" in params_set:
        return "date_range"
    if params_set.intersection(ID_PARAM_TO_SEED_KEY):
        return "id_based"
    return "special"


def iter_year_dates(year: int):
    current = date(year, 1, 1)
    end = date(year, 12, 31)
    while current <= end:
        yield current.isoformat()
        current += timedelta(days=1)


def serialize_response_data(value: Any) -> Any:
    if isinstance(value, bytes):
        return {
            "encoding": "base64",
            "byte_length": len(value),
            "sha256": hashlib.sha256(value).hexdigest(),
            "data_base64": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [serialize_response_data(v) for v in value]
    if isinstance(value, tuple):
        return [serialize_response_data(v) for v in value]
    if isinstance(value, dict):
        return {str(k): serialize_response_data(v) for k, v in value.items()}
    return str(value)


def parse_years_arg(value: str) -> list[int]:
    years: list[int] = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        years.append(int(token))
    if not years:
        raise ValueError("--years 不能为空")
    for y in years:
        if y < 2000 or y > 2100:
            raise ValueError(f"年份超出合理范围: {y}")
    return sorted(set(years))


def request_key(kwargs: dict[str, Any]) -> str:
    """Create a stable key for request kwargs to support resume/skip."""
    return json.dumps(kwargs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def get_completed_request_keys(envelope: dict[str, Any] | None) -> set[str]:
    keys: set[str] = set()
    if not isinstance(envelope, dict):
        return keys
    for item in envelope.get("data", []):
        if not isinstance(item, dict):
            continue
        req = item.get("request")
        if isinstance(req, dict):
            keys.add(request_key(req))
    return keys


def read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def extract_items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "activities", "activityList", "workouts", "trainingPlanList", "goals"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
    return []


def get_activity_date_str(activity: dict[str, Any]) -> str:
    raw = activity.get("startTimeLocal") or activity.get("startTimeGMT")
    if isinstance(raw, str) and raw:
        return raw[:10]
    return ""


def safe_call(client: Any, method: str, kwargs: dict[str, Any], retries: int = 2):
    fn = getattr(client, method, None)
    if fn is None:
        raise AttributeError(f"Garmin client 缺少方法: {method}")

    last_exc: Exception | None = None
    started = time.perf_counter()

    for _ in range(retries + 1):
        try:
            result = fn(**kwargs)
            return result, time.perf_counter() - started
        except Exception as exc:  # pragma: no cover - runtime behavior
            # 4xx parameter/feature errors are deterministic; retry only adds noise.
            if "400 Client Error" in str(exc) or "(400)" in str(exc):
                raise exc
            last_exc = exc
    assert last_exc is not None
    raise last_exc


def fetch_activities_for_year(client: Any, year: int) -> list[dict[str, Any]]:
    activities: list[dict[str, Any]] = []
    page = 0
    limit = 100
    empty_pages = 0

    while page < 500:
        try:
            batch, _ = safe_call(client, "get_activities", {"start": page * limit, "limit": limit}, retries=1)
        except Exception:
            break

        if not isinstance(batch, list) or not batch:
            empty_pages += 1
            if empty_pages >= 2:
                break
            page += 1
            continue

        empty_pages = 0
        year_hits = 0
        has_older = False

        for act in batch:
            if not isinstance(act, dict):
                continue
            date_str = get_activity_date_str(act)
            if date_str.startswith(f"{year}-"):
                activities.append(act)
                year_hits += 1
            elif date_str and date_str < f"{year}-01-01":
                has_older = True

        page += 1
        if year_hits == 0 and has_older:
            break

    return activities


def fetch_all_workouts(client: Any) -> list[dict[str, Any]]:
    workouts: list[dict[str, Any]] = []
    start = 0
    limit = 100

    while start < 20000:
        payload, _ = safe_call(client, "get_workouts", {"start": start, "limit": limit}, retries=1)
        items = extract_items(payload)
        if not items:
            break
        workouts.extend([w for w in items if isinstance(w, dict)])
        if len(items) < limit:
            break
        start += limit

    return workouts


def build_seed_context(client: Any, year: int) -> dict[str, Any]:
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    seeds: dict[str, Any] = {
        "year": year,
        "start_date": start_date,
        "end_date": end_date,
        "dates": list(iter_year_dates(year)),
        "activity_ids": [],
        "workout_ids": [],
        "scheduled_workout_ids": [],
        "device_ids": [],
        "user_profile_numbers": [],
        "gear_uuids": [],
        "plan_ids": [],
        "cached_method_data": {},
    }

    try:
        activities = fetch_activities_for_year(client, year)
    except Exception:
        activities = []
    seeds["cached_method_data"]["get_activities"] = activities
    seeds["activity_ids"] = [a.get("activityId") for a in activities if isinstance(a, dict) and a.get("activityId")]

    try:
        workouts = fetch_all_workouts(client)
    except Exception:
        workouts = []
    seeds["cached_method_data"]["get_workouts"] = workouts
    seeds["workout_ids"] = [
        w.get("workoutId")
        for w in workouts
        if isinstance(w, dict) and w.get("workoutId") is not None
    ]
    seeds["scheduled_workout_ids"] = [
        w.get("scheduledWorkoutId")
        for w in workouts
        if isinstance(w, dict) and w.get("scheduledWorkoutId") is not None
    ]

    try:
        devices, _ = safe_call(client, "get_devices", {}, retries=1)
    except Exception:
        devices = []
    seeds["cached_method_data"]["get_devices"] = devices
    if isinstance(devices, list):
        seeds["device_ids"] = [
            d.get("deviceId")
            for d in devices
            if isinstance(d, dict) and d.get("deviceId") is not None
        ]

    profile = {}
    try:
        profile, _ = safe_call(client, "get_user_profile", {}, retries=1)
    except Exception:
        profile = {}
    seeds["cached_method_data"]["get_user_profile"] = profile
    if isinstance(profile, dict):
        for key in ("userProfileNumber", "profileId"):
            if profile.get(key) is not None:
                seeds["user_profile_numbers"].append(profile[key])

    try:
        last_used, _ = safe_call(client, "get_device_last_used", {}, retries=1)
    except Exception:
        last_used = {}
    seeds["cached_method_data"]["get_device_last_used"] = last_used
    if isinstance(last_used, dict):
        if last_used.get("userProfileNumber") is not None:
            seeds["user_profile_numbers"].append(last_used["userProfileNumber"])
        if last_used.get("deviceId") is not None:
            seeds["device_ids"].append(last_used["deviceId"])

    seeds["user_profile_numbers"] = sorted(set(seeds["user_profile_numbers"]))
    seeds["device_ids"] = sorted(set(seeds["device_ids"]))

    gears: list[dict[str, Any]] = []
    if seeds["user_profile_numbers"]:
        try:
            gear_payload, _ = safe_call(
                client,
                "get_gear",
                {"userProfileNumber": seeds["user_profile_numbers"][0]},
                retries=1,
            )
            if isinstance(gear_payload, list):
                gears = [g for g in gear_payload if isinstance(g, dict)]
            elif isinstance(gear_payload, dict):
                gears = [g for g in extract_items(gear_payload) if isinstance(g, dict)]
        except Exception:
            gears = []
    seeds["cached_method_data"]["get_gear"] = gears
    seeds["gear_uuids"] = [g.get("uuid") for g in gears if g.get("uuid")]

    training_plans = {}
    try:
        training_plans, _ = safe_call(client, "get_training_plans", {}, retries=1)
    except Exception:
        training_plans = {}
    seeds["cached_method_data"]["get_training_plans"] = training_plans
    if isinstance(training_plans, dict):
        plans = training_plans.get("trainingPlanList")
        if isinstance(plans, list):
            seeds["plan_ids"] = [
                p.get("trainingPlanId") for p in plans if isinstance(p, dict) and p.get("trainingPlanId") is not None
            ]

    seeds["activity_ids"] = sorted(set(seeds["activity_ids"]))
    seeds["workout_ids"] = sorted(set(seeds["workout_ids"]))
    seeds["scheduled_workout_ids"] = sorted(set(seeds["scheduled_workout_ids"]))
    seeds["gear_uuids"] = sorted(set(seeds["gear_uuids"]))
    seeds["plan_ids"] = sorted(set(seeds["plan_ids"]))
    return seeds


def run_special_method_calls(method: str, ctx: dict[str, Any]) -> list[dict[str, Any]]:
    start_date = ctx["start_date"]
    end_date = ctx["end_date"]
    if method == "get_lactate_threshold":
        return [{"latest": False, "start_date": start_date, "end_date": end_date, "aggregation": "daily"}]
    if method == "get_goals":
        return [
            {"status": "active", "start": 0, "limit": 100},
            {"status": "completed", "start": 0, "limit": 100},
        ]
    if method == "get_race_predictions":
        return [{"startdate": start_date, "enddate": end_date, "_type": "running"}]
    if method == "get_progress_summary_between_dates":
        return [
            {
                "startdate": start_date,
                "enddate": end_date,
                "metric": "distance",
                "groupbyactivities": True,
            }
        ]
    return []


def chunk_date_range(start_iso: str, end_iso: str, max_days: int) -> list[tuple[str, str]]:
    start_dt = datetime.strptime(start_iso, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_iso, "%Y-%m-%d").date()
    chunks: list[tuple[str, str]] = []
    current = start_dt
    while current <= end_dt:
        chunk_end = min(current + timedelta(days=max_days - 1), end_dt)
        chunks.append((current.isoformat(), chunk_end.isoformat()))
        current = chunk_end + timedelta(days=1)
    return chunks


def build_calls_for_method(
    method: str,
    signature: str,
    call_type: str,
    ctx: dict[str, Any],
    include_downloads: bool,
) -> tuple[list[dict[str, Any]], str | None]:
    params = parse_signature_params(signature)
    params_set = set(params)

    if call_type == "download" and not include_downloads:
        return [], "download_disabled"

    if call_type == "noarg":
        return [{}], None

    if call_type == "daily":
        date_param = "cdate" if "cdate" in params_set else "fordate" if "fordate" in params_set else params[0]
        return [{date_param: d} for d in ctx["dates"]], None

    if call_type == "date_range":
        kwargs: dict[str, Any] = {}
        if "startdate" in params_set:
            kwargs["startdate"] = ctx["start_date"]
        if "enddate" in params_set:
            kwargs["enddate"] = ctx["end_date"]
        if "start_date" in params_set:
            kwargs["start_date"] = ctx["start_date"]
        if "end_date" in params_set:
            kwargs["end_date"] = ctx["end_date"]
        if "start" in params_set and "end" in params_set:
            kwargs["start"] = ctx["start_date"]
            kwargs["end"] = ctx["end_date"]
        if not kwargs:
            return [], "date_range_unresolved"

        # CN endpoint for body battery rejects very long ranges (e.g. full year).
        if method == "get_body_battery" and "startdate" in kwargs and "enddate" in kwargs:
            return [
                {"startdate": s, "enddate": e}
                for s, e in chunk_date_range(kwargs["startdate"], kwargs["enddate"], max_days=31)
            ], None

        return [kwargs], None

    if call_type == "weekly":
        kwargs: dict[str, Any] = {}
        if "start" in params_set:
            kwargs["start"] = ctx["start_date"]
        if "end" in params_set:
            kwargs["end"] = ctx["end_date"]
        if "weeks" in params_set:
            kwargs["weeks"] = 52
        return [kwargs], None

    if call_type == "paged":
        # paged calls are executed by dedicated loop
        return [], None

    if call_type == "id_based" or call_type == "download":
        for param, seed_key in ID_PARAM_TO_SEED_KEY.items():
            if param not in params_set:
                continue
            ids = ctx.get(seed_key, [])
            if not ids:
                return [], f"missing_seed:{seed_key}"
            calls = [{param: id_value} for id_value in ids]
            return calls, None
        return [], "id_param_not_mapped"

    if call_type == "special":
        calls = run_special_method_calls(method, ctx)
        if not calls:
            if not params:
                return [{}], None
            return [], "special_unresolved"
        return calls, None

    return [], "unsupported_call_type"


def execute_paged_method(
    client: Any,
    method: str,
    base_kwargs: dict[str, Any] | None = None,
    start_from: int = 0,
    log_prefix: str = "",
    on_chunk_done: Callable[[dict[str, Any], Any | None, str | None, float], None] | None = None,
) -> float:
    base_kwargs = base_kwargs or {}
    page_start = max(0, start_from)
    limit = int(base_kwargs.get("limit", 100))
    elapsed = 0.0
    chunk_no = 0

    while page_start < 20000:
        kwargs = dict(base_kwargs)
        kwargs["start"] = page_start
        kwargs["limit"] = limit
        chunk_no += 1
        print(f"{log_prefix}开始分页块 #{chunk_no}: {kwargs}")
        try:
            result, took = safe_call(client, method, kwargs, retries=1)
            elapsed += took
            serialized = serialize_response_data(result)
            if on_chunk_done:
                on_chunk_done(kwargs, serialized, None, took)
            print(f"{log_prefix}完成分页块 #{chunk_no}，耗时 {took:.2f}s")
            items = extract_items(result)
            if not items:
                break
            if len(items) < limit:
                break
            page_start += limit
        except Exception as exc:
            if on_chunk_done:
                on_chunk_done(kwargs, None, str(exc), 0.0)
            print(f"{log_prefix}分页块 #{chunk_no} 失败: {exc}")
            break
    return elapsed


def execute_method_for_year(
    client: Any,
    spec: dict[str, str],
    ctx: dict[str, Any],
    include_downloads: bool,
    output_file: Path | None = None,
    existing_envelope: dict[str, Any] | None = None,
    log_prefix: str = "",
) -> dict[str, Any]:
    method = spec["method"]
    signature = spec["signature"]
    call_type = classify_call_type(method, signature)

    if isinstance(existing_envelope, dict) and existing_envelope.get("method") == method:
        envelope: dict[str, Any] = existing_envelope
        envelope["method"] = method
        envelope["section"] = spec["section"]
        envelope["year"] = ctx["year"]
        envelope["call_type"] = call_type
    else:
        envelope = {
            "method": method,
            "section": spec["section"],
            "year": ctx["year"],
            "call_type": call_type,
            "status": "pending",
            "request_args": [],
            "data": [],
            "errors": [],
            "stats": {
                "attempted_calls": 0,
                "success_calls": 0,
                "failed_calls": 0,
                "duration_seconds": 0.0,
            },
        }

    if not isinstance(envelope.get("request_args"), list):
        envelope["request_args"] = []
    if not isinstance(envelope.get("data"), list):
        envelope["data"] = []
    if not isinstance(envelope.get("errors"), list):
        envelope["errors"] = []
    if not isinstance(envelope.get("stats"), dict):
        envelope["stats"] = {}
    envelope["stats"]["attempted_calls"] = len(envelope["request_args"])
    envelope["stats"]["success_calls"] = len(envelope["data"])
    envelope["stats"]["failed_calls"] = len(envelope["errors"])
    envelope["stats"]["duration_seconds"] = float(envelope["stats"].get("duration_seconds", 0.0))

    completed_keys = get_completed_request_keys(envelope)

    cached_data = ctx.get("cached_method_data", {}).get(method)
    if cached_data not in (None, {}, []) and envelope["stats"]["success_calls"] == 0:
        print(f"{log_prefix}使用 seed cache，开始写入")
        envelope["request_args"].append({"source": "seed_cache"})
        envelope["data"].append({"request": {"source": "seed_cache"}, "response": serialize_response_data(cached_data)})
        envelope["stats"]["attempted_calls"] = len(envelope["request_args"])
        envelope["stats"]["success_calls"] = len(envelope["data"])
        envelope["status"] = "success"
        if output_file:
            write_json(output_file, envelope)
        print(f"{log_prefix}seed cache 写入完成")
        return envelope

    if call_type == "paged":
        extra = {}
        if method == "get_activities":
            extra["limit"] = 100
        if method == "get_workouts":
            extra["limit"] = 100

        resume_start = 0
        if envelope["data"]:
            starts = [
                item.get("request", {}).get("start")
                for item in envelope["data"]
                if isinstance(item, dict)
                and isinstance(item.get("request"), dict)
                and isinstance(item.get("request", {}).get("start"), int)
            ]
            if starts:
                resume_start = max(starts) + int(extra.get("limit", 100))

        if resume_start > 0:
            print(f"{log_prefix}检测到已完成分页块，断点续跑 start={resume_start}")
        else:
            print(f"{log_prefix}开始分页拉取")

        def on_paged_chunk_done(req: dict[str, Any], response: Any | None, error: str | None, took: float):
            envelope["request_args"].append(req)
            if error is None:
                envelope["data"].append({"request": req, "response": response})
            else:
                envelope["errors"].append({"request": req, "error": error})
            envelope["stats"]["attempted_calls"] = len(envelope["request_args"])
            envelope["stats"]["success_calls"] = len(envelope["data"])
            envelope["stats"]["failed_calls"] = len(envelope["errors"])
            envelope["stats"]["duration_seconds"] = round(float(envelope["stats"]["duration_seconds"]) + took, 3)
            if output_file:
                write_json(output_file, envelope)

        execute_paged_method(
            client,
            method,
            base_kwargs=extra,
            start_from=resume_start,
            log_prefix=log_prefix,
            on_chunk_done=on_paged_chunk_done,
        )

        if envelope["stats"]["success_calls"] > 0 and envelope["stats"]["failed_calls"] == 0:
            envelope["status"] = "success"
        elif envelope["stats"]["success_calls"] > 0:
            envelope["status"] = "partial"
        else:
            envelope["status"] = "failed"
        return envelope

    call_kwargs_list, skip_reason = build_calls_for_method(method, signature, call_type, ctx, include_downloads)
    if skip_reason is not None and not call_kwargs_list:
        envelope["status"] = "skipped"
        envelope["errors"].append({"error": skip_reason})
        envelope["stats"]["attempted_calls"] = len(envelope["request_args"])
        envelope["stats"]["success_calls"] = len(envelope["data"])
        envelope["stats"]["failed_calls"] = len(envelope["errors"])
        if output_file:
            write_json(output_file, envelope)
        return envelope

    pending_calls = [kwargs for kwargs in call_kwargs_list if request_key(kwargs) not in completed_keys]
    skipped_count = len(call_kwargs_list) - len(pending_calls)
    print(f"{log_prefix}总块数 {len(call_kwargs_list)}，已完成跳过 {skipped_count}，待执行 {len(pending_calls)}")

    for idx, kwargs in enumerate(pending_calls, start=1):
        print(f"{log_prefix}开始块 {idx}/{len(pending_calls)}: {kwargs}")
        started = time.perf_counter()
        try:
            result, elapsed = safe_call(client, method, kwargs, retries=1)
            envelope["request_args"].append(kwargs)
            envelope["data"].append({"request": kwargs, "response": serialize_response_data(result)})
            envelope["stats"]["duration_seconds"] = round(float(envelope["stats"]["duration_seconds"]) + elapsed, 3)
            print(f"{log_prefix}完成块 {idx}/{len(pending_calls)}，耗时 {elapsed:.2f}s")
        except Exception as exc:
            elapsed = time.perf_counter() - started
            envelope["request_args"].append(kwargs)
            envelope["errors"].append({"request": kwargs, "error": str(exc)})
            envelope["stats"]["duration_seconds"] = round(float(envelope["stats"]["duration_seconds"]) + elapsed, 3)
            print(f"{log_prefix}失败块 {idx}/{len(pending_calls)}，耗时 {elapsed:.2f}s，错误: {exc}")
        envelope["stats"]["attempted_calls"] = len(envelope["request_args"])
        envelope["stats"]["success_calls"] = len(envelope["data"])
        envelope["stats"]["failed_calls"] = len(envelope["errors"])
        if output_file:
            write_json(output_file, envelope)

    if envelope["stats"]["success_calls"] > 0 and envelope["stats"]["failed_calls"] == 0:
        envelope["status"] = "success"
    elif envelope["stats"]["success_calls"] > 0:
        envelope["status"] = "partial"
    elif envelope["stats"]["attempted_calls"] == 0:
        envelope["status"] = "skipped"
    else:
        envelope["status"] = "failed"

    return envelope


def write_json(path: Path, payload: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def collect_year_data(
    client: Any,
    methods: list[dict[str, str]],
    year: int,
    output_root: Path,
    overwrite: bool,
    include_downloads: bool,
    selected_sections: set[str] | None,
    max_workers: int = 1,
    client_factory: Callable[[], Any] | None = None,
) -> Path:
    report_root = output_root / f"garmin_report_{year}"
    data_root = report_root / "data"

    if overwrite and data_root.exists():
        shutil.rmtree(data_root)
    data_root.mkdir(parents=True, exist_ok=True)

    ctx = build_seed_context(client, year)
    indexed_specs: list[tuple[int, dict[str, str]]] = []
    for index, spec in enumerate(methods):
        section_slug = spec["section_slug"]
        if selected_sections and section_slug not in selected_sections:
            continue
        if spec["method"] in EXCLUDED_METHODS:
            print(f"[{year}] [{section_slug}/{spec['method']}] 已配置排除，跳过")
            continue
        indexed_specs.append((index, spec))

    worker_local = threading.local()

    def get_worker_client(log_prefix: str) -> Any:
        if max_workers <= 1 or client_factory is None:
            return client
        worker_client = getattr(worker_local, "client", None)
        if worker_client is None:
            print(f"{log_prefix}初始化并行 worker 客户端")
            worker_client = client_factory()
            worker_local.client = worker_client
        return worker_client

    def run_method(spec: dict[str, str]) -> dict[str, Any]:
        section_slug = spec["section_slug"]
        output_file = data_root / section_slug / f"{spec['method']}.json"
        log_prefix = f"[{year}] [{section_slug}/{spec['method']}] "
        call_type = classify_call_type(spec["method"], spec["signature"])
        existing_envelope = None
        method_client = get_worker_client(log_prefix)

        try:
            if output_file.exists() and not overwrite:
                existing_envelope = read_json_if_exists(output_file)
                if isinstance(existing_envelope, dict) and existing_envelope.get("status") in {"success", "skipped"}:
                    print(f"{log_prefix}已完成，跳过")
                    envelope = existing_envelope
                else:
                    method_started = time.perf_counter()
                    print(f"{log_prefix}断点续跑")
                    envelope = execute_method_for_year(
                        method_client,
                        spec,
                        ctx,
                        include_downloads,
                        output_file=output_file,
                        existing_envelope=existing_envelope,
                        log_prefix=log_prefix,
                    )
                    write_json(output_file, envelope)
                    print(f"{log_prefix}完成，状态 {envelope['status']}，总耗时 {time.perf_counter() - method_started:.2f}s")
            else:
                method_started = time.perf_counter()
                print(f"{log_prefix}开始拉取")
                envelope = execute_method_for_year(
                    method_client,
                    spec,
                    ctx,
                    include_downloads,
                    output_file=output_file,
                    existing_envelope=existing_envelope,
                    log_prefix=log_prefix,
                )
                write_json(output_file, envelope)
                print(f"{log_prefix}完成，状态 {envelope['status']}，总耗时 {time.perf_counter() - method_started:.2f}s")

        except Exception as exc:
            envelope = {
                "method": spec["method"],
                "section": spec["section"],
                "year": year,
                "call_type": call_type,
                "status": "failed",
                "request_args": [],
                "data": [],
                "errors": [{"error": str(exc)}],
                "stats": {
                    "attempted_calls": 0,
                    "success_calls": 0,
                    "failed_calls": 1,
                    "duration_seconds": 0.0,
                },
            }
            write_json(output_file, envelope)
            print(f"{log_prefix}执行异常: {exc}")

        return {
            "method": spec["method"],
            "section": spec["section"],
            "section_slug": section_slug,
            "call_type": envelope.get("call_type", call_type),
            "status": envelope.get("status", "failed"),
            "output_file": str(output_file.relative_to(report_root)),
            "stats": envelope.get("stats", {}),
            "error_count": len(envelope.get("errors", [])),
        }

    manifest_items: list[dict[str, Any]] = []
    if max_workers > 1 and len(indexed_specs) > 1:
        worker_count = min(max_workers, len(indexed_specs))
        print(f"[{year}] 并行拉取已启用，worker={worker_count}")
        manifest_by_index: dict[int, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_index = {
                executor.submit(run_method, spec): index
                for index, spec in indexed_specs
            }
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                manifest_by_index[index] = future.result()
        for index, _ in indexed_specs:
            if index in manifest_by_index:
                manifest_items.append(manifest_by_index[index])
    else:
        for _, spec in indexed_specs:
            manifest_items.append(run_method(spec))

    status_counts = {
        "success": 0,
        "partial": 0,
        "failed": 0,
        "skipped": 0,
        "pending": 0,
    }
    for item in manifest_items:
        status = item["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    manifest = {
        "year": year,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_methods": len(manifest_items),
            "status_counts": status_counts,
        },
        "methods": manifest_items,
    }

    manifest_path = data_root / "_manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path


def build_client(email: str, password: str, is_cn: bool):
    try:
        from garminconnect import Garmin  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "缺少依赖 garminconnect。请先执行: python3 -m pip install garminconnect"
        ) from exc

    client = Garmin(email=email, password=password, is_cn=is_cn)
    client.login()
    return client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Garmin 全接口分类型拉取工具")
    parser.add_argument("--email", help="Garmin 邮箱，默认读取 GARMIN_EMAIL")
    parser.add_argument("--password", help="Garmin 密码，默认读取 GARMIN_PASSWORD")
    parser.add_argument("--years", default="2023,2024,2025", help="逗号分隔年份，例如 2023,2024,2025")
    parser.add_argument("--api-doc", default=str(API_DOC_DEFAULT), help="接口文档路径")
    parser.add_argument("--output-root", default=".", help="输出根目录，默认当前目录")
    parser.add_argument("--sections", default="", help="可选，逗号分隔 section_slug，仅执行子集")

    parser.add_argument("--is-cn", dest="is_cn", action="store_true", help="使用中国区 Garmin")
    parser.add_argument("--no-is-cn", dest="is_cn", action="store_false", help="使用国际区 Garmin")
    parser.set_defaults(is_cn=None)

    parser.add_argument("--overwrite", dest="overwrite", action="store_true", help="覆盖已存在分类数据")
    parser.add_argument("--no-overwrite", dest="overwrite", action="store_false", help="不覆盖已存在分类数据")
    parser.set_defaults(overwrite=False)

    parser.add_argument("--include-downloads", dest="include_downloads", action="store_true", help="包含 download_* 接口（默认）")
    parser.add_argument("--no-include-downloads", dest="include_downloads", action="store_false", help="跳过 download_* 接口")
    parser.set_defaults(include_downloads=True)
    parser.add_argument("--max-workers", type=int, default=1, help="方法级并发 worker 数，默认 1（串行）")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    email = args.email or os.getenv("GARMIN_EMAIL")
    password = args.password or os.getenv("GARMIN_PASSWORD")
    if not email or not password:
        print("❌ 缺少 Garmin 账号或密码，请使用 --email/--password 或 GARMIN_EMAIL/GARMIN_PASSWORD")
        return 2

    years = parse_years_arg(args.years)
    if args.max_workers < 1:
        print("❌ --max-workers 必须 >= 1")
        return 2
    doc_path = Path(args.api_doc)
    output_root = Path(args.output_root)

    env_cn = os.getenv("GARMIN_CN")
    default_cn = True if env_cn is None else env_cn.lower() in {"1", "true", "yes", "y"}
    is_cn = default_cn if args.is_cn is None else bool(args.is_cn)

    methods = parse_api_reference(doc_path)
    if len(methods) == 0:
        print(f"❌ 在文档中未解析到接口: {doc_path}")
        return 3

    sections_filter: set[str] | None = None
    if args.sections.strip():
        sections_filter = {x.strip() for x in args.sections.split(",") if x.strip()}

    print("=" * 72)
    print("Garmin 分类数据拉取")
    print("=" * 72)
    print(f"年份: {years}")
    print(f"区域: {'中国区' if is_cn else '国际区'}")
    print(f"接口文档: {doc_path}")
    print(f"解析接口数: {len(methods)}")
    print(f"包含下载接口: {args.include_downloads}")
    print(f"覆盖模式: {args.overwrite}")
    print(f"方法并发数: {args.max_workers}")
    if args.max_workers > 1:
        print("并发说明: 每个 worker 使用独立登录会话，避免共享会话并发冲突")
    if sections_filter:
        print(f"Section 过滤: {sorted(sections_filter)}")
    print("=" * 72)

    try:
        client = build_client(email=email, password=password, is_cn=is_cn)
    except Exception as exc:
        print(f"❌ 登录失败: {exc}")
        return 4

    worker_client_factory: Callable[[], Any] | None = None
    if args.max_workers > 1:
        worker_client_factory = lambda: build_client(email=email, password=password, is_cn=is_cn)

    manifest_paths: list[Path] = []
    for year in years:
        print(f"\n>>> 开始拉取 {year} 年...")
        manifest_path = collect_year_data(
            client=client,
            methods=methods,
            year=year,
            output_root=output_root,
            overwrite=args.overwrite,
            include_downloads=args.include_downloads,
            selected_sections=sections_filter,
            max_workers=args.max_workers,
            client_factory=worker_client_factory,
        )
        manifest_paths.append(manifest_path)
        print(f"✓ {year} 年完成，manifest: {manifest_path}")

    print("\n全部年份执行完成。")
    for p in manifest_paths:
        print(f"- {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
