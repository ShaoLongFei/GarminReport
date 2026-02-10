#!/usr/bin/env python3
from __future__ import annotations

import argparse
import calendar
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any


SPORT_GROUPS: dict[str, set[str]] = {
    "running": {"running", "treadmill_running"},
    "swimming": {"lap_swimming"},
    "badminton": {"badminton"},
    "strength_training": {"strength_training"},
    "cycling": {"cycling"},
}

SPORT_TYPE_ZH: dict[str, str] = {
    "running": "跑步",
    "treadmill_running": "跑步机跑步",
    "lap_swimming": "游泳",
    "open_water_swimming": "公开水域游泳",
    "badminton": "羽毛球",
    "strength_training": "力量训练",
    "cycling": "骑行",
    "indoor_cardio": "有氧训练",
    "table_tennis": "乒乓球",
    "walking": "步行",
    "hiking": "徒步",
    "yoga": "瑜伽",
    "other": "其他运动",
    "unknown": "未知类型",
}


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        if isinstance(value, str) and value.strip():
            return float(value.strip())
    except ValueError:
        return None
    return None


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def pace_min_per_km(distance_m: Any, duration_s: Any) -> float | None:
    d = _to_float(distance_m)
    t = _to_float(duration_s)
    if d is None or t is None or d <= 0 or t <= 0:
        return None
    return round((t / 60.0) / (d / 1000.0), 3)


def pace_min_per_100m(distance_m: Any, duration_s: Any) -> float | None:
    d = _to_float(distance_m)
    t = _to_float(duration_s)
    if d is None or t is None or d <= 0 or t <= 0:
        return None
    return round((t / 60.0) / (d / 100.0), 3)


def _month_buckets() -> dict[str, float]:
    return {f"{i:02d}": 0.0 for i in range(1, 13)}


def _safe_date_prefix(value: Any) -> str | None:
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return None


def _month_from_date(value: Any) -> str | None:
    d = _safe_date_prefix(value)
    if d is None or len(d) < 7:
        return None
    mm = d[5:7]
    if mm.isdigit() and 1 <= int(mm) <= 12:
        return mm
    return None


def resolve_method_file(report_dir: Path, section_slug: str, method: str) -> Path:
    new_path = report_dir / "data" / section_slug / f"{method}.json"
    old_path = report_dir / "data" / "classified" / section_slug / f"{method}.json"
    if new_path.exists():
        return new_path
    if old_path.exists():
        return old_path
    return new_path


def _flatten_envelope_with_meta(payload: Any) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    dropped = 0

    def consume_response(response: Any):
        nonlocal dropped
        if isinstance(response, dict):
            rows.append(response)
            return
        if isinstance(response, list):
            for item in response:
                if isinstance(item, dict):
                    rows.append(item)
                else:
                    dropped += 1
            return
        if response is None:
            return
        dropped += 1

    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        for item in payload["data"]:
            if isinstance(item, dict):
                consume_response(item.get("response"))
            else:
                dropped += 1
        return rows, dropped

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                rows.append(item)
            else:
                dropped += 1
        return rows, dropped

    if isinstance(payload, dict):
        rows.append(payload)
        return rows, dropped

    return rows, dropped + 1


def flatten_envelope_responses(payload: Any) -> list[dict[str, Any]]:
    rows, _ = _flatten_envelope_with_meta(payload)
    return rows


def _load_source(
    report_dir: Path,
    section_slug: str,
    method: str,
    warnings: list[str],
) -> dict[str, Any]:
    path = resolve_method_file(report_dir, section_slug, method)
    source = {
        "section": section_slug,
        "method": method,
        "path": str(path.relative_to(report_dir)),
        "exists": path.exists(),
        "status": "missing",
        "records": [],
        "dropped": 0,
    }
    if not path.exists():
        warnings.append(f"missing source file: {path}")
        return source

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        warnings.append(f"failed to parse source {path}: {exc}")
        source["status"] = "parse_error"
        return source

    if isinstance(payload, dict):
        source["status"] = str(payload.get("status", "unknown"))
    else:
        source["status"] = "legacy"

    rows, dropped = _flatten_envelope_with_meta(payload)
    source["records"] = rows
    source["dropped"] = dropped

    if source["status"] not in {"success", "legacy"}:
        warnings.append(f"source status is {source['status']}: {path}")
    return source


def _activity_type_key(activity: dict[str, Any]) -> str:
    raw = activity.get("activityType")
    if isinstance(raw, dict):
        return str(raw.get("typeKey") or raw.get("parentTypeKey") or "unknown")
    if isinstance(raw, str) and raw:
        return raw
    return "unknown"


def _activity_date(activity: dict[str, Any]) -> str | None:
    return _safe_date_prefix(activity.get("startTimeLocal")) or _safe_date_prefix(activity.get("startTimeGMT"))


def _activity_brief(activity: dict[str, Any]) -> dict[str, Any]:
    distance = _to_float(activity.get("distance")) or 0.0
    duration = _to_float(activity.get("duration")) or 0.0
    calories = _to_float(activity.get("calories")) or 0.0
    return {
        "activity_id": activity.get("activityId"),
        "activity_name": activity.get("activityName"),
        "type_key": _activity_type_key(activity),
        "date": _activity_date(activity),
        "distance_m": round(distance, 3),
        "duration_s": round(duration, 3),
        "calories": round(calories, 3),
    }


def _build_activity_overview(
    activities: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, float], dict[str, float], dict[str, int], dict[str, dict[str, float]]]:
    active_days: set[str] = set()
    total_distance = 0.0
    total_duration = 0.0
    total_calories = 0.0
    total_elevation = 0.0
    longest_duration: dict[str, Any] | None = None
    longest_distance: dict[str, Any] | None = None
    count_by_month = {k: 0 for k in _month_buckets()}
    distance_by_month = _month_buckets()
    daily_duration_h: dict[str, float] = {}
    daily_calories: dict[str, float] = {}

    for act in activities:
        d = _to_float(act.get("distance")) or 0.0
        t = _to_float(act.get("duration")) or 0.0
        cals = _to_float(act.get("calories")) or 0.0
        elev = _to_float(act.get("elevationGain")) or 0.0
        dt = _activity_date(act)
        if dt:
            active_days.add(dt)
        mm = _month_from_date(dt)
        if mm:
            count_by_month[mm] += 1
            distance_by_month[mm] += d

        if dt:
            daily_duration_h[dt] = daily_duration_h.get(dt, 0.0) + (t / 3600.0)
            daily_calories[dt] = daily_calories.get(dt, 0.0) + cals

        total_distance += d
        total_duration += t
        total_calories += cals
        total_elevation += elev

        if longest_duration is None or t > (_to_float(longest_duration.get("duration_s")) or 0.0):
            longest_duration = {
                "activity_id": act.get("activityId"),
                "activity_name": act.get("activityName"),
                "type_key": _activity_type_key(act),
                "date": dt,
                "duration_s": round(t, 3),
            }
        if longest_distance is None or d > (_to_float(longest_distance.get("distance_m")) or 0.0):
            longest_distance = {
                "activity_id": act.get("activityId"),
                "activity_name": act.get("activityName"),
                "type_key": _activity_type_key(act),
                "date": dt,
                "distance_m": round(d, 3),
            }

    overview = {
        "total_activities": len(activities),
        "active_days": len(active_days),
        "total_distance_m": round(total_distance, 3),
        "total_duration_s": round(total_duration, 3),
        "total_calories": round(total_calories, 3),
        "total_elevation_gain_m": round(total_elevation, 3),
        "longest_activity": longest_duration,
        "longest_distance_activity": longest_distance,
        "top_activities_by_duration": [
            _activity_brief(act)
            for act in sorted(activities, key=lambda x: _to_float(x.get("duration")) or 0.0, reverse=True)[:10]
        ],
    }
    daily_trends = {
        "duration_h_by_date": {k: round(v, 3) for k, v in sorted(daily_duration_h.items())},
        "calories_by_date": {k: round(v, 3) for k, v in sorted(daily_calories.items())},
    }
    return (
        overview,
        distance_by_month,
        {k: float(v) for k, v in count_by_month.items()},
        {k: int(v) for k, v in count_by_month.items()},
        daily_trends,
    )


def _build_sport_metrics(activities: list[dict[str, Any]], sport_name: str) -> dict[str, Any]:
    total_distance = 0.0
    total_duration = 0.0
    total_calories = 0.0
    longest_distance = 0.0
    longest_duration = 0.0
    hr_values: list[float] = []
    total_sets = 0.0
    total_reps = 0.0

    for act in activities:
        d = _to_float(act.get("distance")) or 0.0
        t = _to_float(act.get("duration")) or 0.0
        total_distance += d
        total_duration += t
        total_calories += _to_float(act.get("calories")) or 0.0
        longest_distance = max(longest_distance, d)
        longest_duration = max(longest_duration, t)

        hr = _to_float(act.get("averageHR"))
        if hr is not None and hr > 0:
            hr_values.append(hr)

        if sport_name == "strength_training":
            total_sets += _to_float(act.get("totalSets")) or 0.0
            total_reps += _to_float(act.get("totalReps")) or 0.0

    metrics = {
        "count": len(activities),
        "total_distance_m": round(total_distance, 3),
        "total_duration_s": round(total_duration, 3),
        "total_calories": round(total_calories, 3),
        "avg_pace_min_per_km": pace_min_per_km(total_distance, total_duration),
        "longest_distance_m": round(longest_distance, 3),
        "longest_duration_s": round(longest_duration, 3),
        "avg_heart_rate": _avg(hr_values),
        "top_activities_by_duration": [
            _activity_brief(act)
            for act in sorted(activities, key=lambda x: _to_float(x.get("duration")) or 0.0, reverse=True)[:5]
        ],
    }

    if sport_name == "swimming":
        metrics["avg_pace_min_per_100m"] = pace_min_per_100m(total_distance, total_duration)
    if sport_name == "strength_training":
        metrics["total_sets"] = int(round(total_sets))
        metrics["total_reps"] = int(round(total_reps))
    return metrics


def _analyze_activities(
    activities_raw: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, dict[str, float]]]:
    deduped: list[dict[str, Any]] = []
    seen_ids: set[Any] = set()
    for act in activities_raw:
        act_id = act.get("activityId")
        dedup_key = act_id if act_id is not None else (act.get("activityName"), act.get("startTimeLocal"), act.get("duration"))
        if dedup_key in seen_ids:
            continue
        seen_ids.add(dedup_key)
        deduped.append(act)

    overview, distance_by_month, _, count_by_month, daily_trends = _build_activity_overview(deduped)

    type_counter = Counter(_activity_type_key(a) for a in deduped)
    type_duration_counter: Counter[str] = Counter()
    type_calories_counter: Counter[str] = Counter()
    type_distance_counter: Counter[str] = Counter()
    for a in deduped:
        key = _activity_type_key(a)
        type_duration_counter[key] += _to_float(a.get("duration")) or 0.0
        type_calories_counter[key] += _to_float(a.get("calories")) or 0.0
        type_distance_counter[key] += _to_float(a.get("distance")) or 0.0

    known_types = set().union(*SPORT_GROUPS.values())
    sports: dict[str, Any] = {}
    for sport_name, type_keys in SPORT_GROUPS.items():
        subset = [a for a in deduped if _activity_type_key(a) in type_keys]
        sports[sport_name] = _build_sport_metrics(subset, sport_name=sport_name)

    other_subset = [a for a in deduped if _activity_type_key(a) not in known_types]
    sports["other_sports"] = _build_sport_metrics(other_subset, sport_name="other_sports")
    sports["sport_type_distribution"] = {k: v for k, v in type_counter.most_common()}
    sports["sport_type_duration_s_distribution"] = {
        k: round(v, 3) for k, v in sorted(type_duration_counter.items(), key=lambda item: item[1], reverse=True)
    }
    sports["sport_type_calories_distribution"] = {
        k: round(v, 3) for k, v in sorted(type_calories_counter.items(), key=lambda item: item[1], reverse=True)
    }
    sports["sport_type_distance_m_distribution"] = {
        k: round(v, 3) for k, v in sorted(type_distance_counter.items(), key=lambda item: item[1], reverse=True)
    }
    sports["sport_type_analysis"] = {
        "by_count": {k: int(v) for k, v in type_counter.most_common()},
        "by_duration_s": {
            k: round(v, 3) for k, v in sorted(type_duration_counter.items(), key=lambda item: item[1], reverse=True)
        },
        "by_calories": {
            k: round(v, 3) for k, v in sorted(type_calories_counter.items(), key=lambda item: item[1], reverse=True)
        },
        "by_distance_m": {
            k: round(v, 3) for k, v in sorted(type_distance_counter.items(), key=lambda item: item[1], reverse=True)
        },
        "display_names_zh": {k: SPORT_TYPE_ZH.get(k, k) for k in type_counter.keys()},
    }

    monthly = {
        "activity_count_by_month": count_by_month,
        "distance_m_by_month": {k: round(v, 3) for k, v in distance_by_month.items()},
    }
    return overview, sports, monthly, daily_trends


def _extract_sleep_dto(row: dict[str, Any]) -> dict[str, Any] | None:
    dto = row.get("dailySleepDTO")
    if isinstance(dto, dict):
        return dto
    return None


def _extract_sleep_score(dto: dict[str, Any]) -> float | None:
    scores = dto.get("sleepScores")
    if isinstance(scores, dict):
        overall = scores.get("overall")
        if isinstance(overall, dict):
            val = _to_float(overall.get("value"))
            if val is not None:
                return val
    direct = _to_float(dto.get("overallSleepScore"))
    if direct is not None:
        return direct
    return None


def _analyze_health(
    year: int,
    user_summary_rows: list[dict[str, Any]],
    sleep_rows: list[dict[str, Any]],
    hrv_rows: list[dict[str, Any]],
    stress_rows: list[dict[str, Any]],
    respiration_rows: list[dict[str, Any]],
    weigh_in_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    daily_rows = [r for r in user_summary_rows if isinstance(r, dict)]
    sleep_dtos = [dto for dto in (_extract_sleep_dto(r) for r in sleep_rows) if isinstance(dto, dict)]
    valid_sleep = [dto for dto in sleep_dtos if (_to_float(dto.get("sleepTimeSeconds")) or 0.0) > 0]

    total_steps = sum((_to_float(r.get("totalSteps")) or 0.0) for r in daily_rows)
    total_distance = sum((_to_float(r.get("totalDistanceMeters")) or 0.0) for r in daily_rows)
    total_active_kcal = sum((_to_float(r.get("activeKilocalories")) or 0.0) for r in daily_rows)
    total_moderate = sum((_to_float(r.get("moderateIntensityMinutes")) or 0.0) for r in daily_rows)
    total_vigorous = sum((_to_float(r.get("vigorousIntensityMinutes")) or 0.0) for r in daily_rows)
    total_intensity_weighted = sum(
        (_to_float(r.get("moderateIntensityMinutes")) or 0.0) + 2.0 * (_to_float(r.get("vigorousIntensityMinutes")) or 0.0)
        for r in daily_rows
    )

    rhr_values = [x for x in ((_to_float(r.get("restingHeartRate")) or 0.0) for r in daily_rows) if x > 0]
    sleep_values = [(_to_float(r.get("sleepTimeSeconds")) or 0.0) for r in valid_sleep]
    deep_values = [(_to_float(r.get("deepSleepSeconds")) or 0.0) for r in valid_sleep]
    light_values = [(_to_float(r.get("lightSleepSeconds")) or 0.0) for r in valid_sleep]
    rem_values = [(_to_float(r.get("remSleepSeconds")) or 0.0) for r in valid_sleep]
    sleep_score_values = [s for s in (_extract_sleep_score(r) for r in valid_sleep) if s is not None]

    days_in_year = 366 if calendar.isleap(year) else 365
    daily_count = len(daily_rows)
    sleep_count = len(valid_sleep)

    steps_by_month = _month_buckets()
    sleep_hours_by_month = _month_buckets()

    for row in daily_rows:
        mm = _month_from_date(row.get("calendarDate"))
        if mm:
            steps_by_month[mm] += _to_float(row.get("totalSteps")) or 0.0

    for dto in valid_sleep:
        mm = _month_from_date(dto.get("calendarDate"))
        if mm:
            sleep_hours_by_month[mm] += (_to_float(dto.get("sleepTimeSeconds")) or 0.0) / 3600.0

    intensity_minutes_by_date: dict[str, float] = {}
    resting_heart_rate_by_date: dict[str, float] = {}
    for row in daily_rows:
        day = _safe_date_prefix(row.get("calendarDate"))
        if not day:
            continue
        moderate = _to_float(row.get("moderateIntensityMinutes")) or 0.0
        vigorous = _to_float(row.get("vigorousIntensityMinutes")) or 0.0
        intensity_minutes_by_date[day] = round(moderate + 2.0 * vigorous, 3)
        rhr = _to_float(row.get("restingHeartRate"))
        if rhr is not None and rhr > 0:
            resting_heart_rate_by_date[day] = round(rhr, 3)

    weight_kg_by_date: dict[str, float] = {}
    body_age_by_date: dict[str, float] = {}
    for row in weigh_in_rows:
        if not isinstance(row, dict):
            continue
        points = row.get("dateWeightList")
        if not isinstance(points, list):
            continue
        for point in points:
            if not isinstance(point, dict):
                continue
            day = _safe_date_prefix(point.get("calendarDate"))
            if not day:
                continue
            weight_grams = _to_float(point.get("weight"))
            if weight_grams is not None and weight_grams > 0:
                weight_kg_by_date[day] = round(weight_grams / 1000.0, 3)
            age_val = _to_float(point.get("metabolicAge"))
            if age_val is None:
                age_val = _to_float(point.get("bodyAge"))
            if age_val is not None and age_val > 0:
                body_age_by_date[day] = round(age_val, 3)

    health_overview = {
        "days_in_year": days_in_year,
        "daily_summary_days": daily_count,
        "sleep_recorded_days": sleep_count,
        "total_steps": int(round(total_steps)),
        "avg_daily_steps": round(total_steps / daily_count, 3) if daily_count else 0.0,
        "total_distance_m": round(total_distance, 3),
        "avg_resting_heart_rate": _avg(rhr_values),
        "total_active_kcal": round(total_active_kcal, 3),
        "total_moderate_intensity_minutes": round(total_moderate, 3),
        "total_vigorous_intensity_minutes": round(total_vigorous, 3),
        "total_intensity_minutes": round(total_intensity_weighted, 3),
        "avg_daily_intensity_minutes": round(total_intensity_weighted / daily_count, 3) if daily_count else 0.0,
        "avg_sleep_hours": round((sum(sleep_values) / sleep_count) / 3600.0, 3) if sleep_count else None,
        "avg_sleep_score": _avg(sleep_score_values),
        "avg_deep_sleep_hours": round((sum(deep_values) / sleep_count) / 3600.0, 3) if sleep_count else None,
        "avg_light_sleep_hours": round((sum(light_values) / sleep_count) / 3600.0, 3) if sleep_count else None,
        "avg_rem_sleep_hours": round((sum(rem_values) / sleep_count) / 3600.0, 3) if sleep_count else None,
    }

    hrv_values: list[float] = []
    for row in hrv_rows:
        if not isinstance(row, dict):
            continue
        summary = row.get("hrvSummary")
        if not isinstance(summary, dict):
            continue
        v = _to_float(summary.get("lastNightAvg"))
        if v is None or v <= 0:
            v = _to_float(summary.get("weeklyAvg"))
        if v is not None and v > 0:
            hrv_values.append(v)

    stress_avg_values = [
        v
        for v in ((_to_float(row.get("avgStressLevel")) or -1.0) for row in stress_rows if isinstance(row, dict))
        if v >= 0
    ]
    stress_max_values = [
        v
        for v in ((_to_float(row.get("maxStressLevel")) or -1.0) for row in stress_rows if isinstance(row, dict))
        if v >= 0
    ]
    respiration_sleep_values = [
        v
        for v in ((_to_float(row.get("avgSleepRespirationValue")) or -1.0) for row in respiration_rows if isinstance(row, dict))
        if v >= 0
    ]

    advanced = {
        "hrv": {
            "days": len(hrv_values),
            "avg": _avg(hrv_values),
            "min": round(min(hrv_values), 3) if hrv_values else None,
            "max": round(max(hrv_values), 3) if hrv_values else None,
        },
        "stress": {
            "days": len(stress_avg_values),
            "avg_daily_stress": _avg(stress_avg_values),
            "max_stress_peak": round(max(stress_max_values), 3) if stress_max_values else None,
        },
        "respiration": {
            "days": len(respiration_sleep_values),
            "avg_sleep_respiration": _avg(respiration_sleep_values),
        },
    }

    monthly = {
        "steps_by_month": {k: int(round(v)) for k, v in steps_by_month.items()},
        "sleep_hours_by_month": {k: round(v, 3) for k, v in sleep_hours_by_month.items()},
    }
    daily = {
        "intensity_minutes_by_date": {k: v for k, v in sorted(intensity_minutes_by_date.items())},
        "resting_heart_rate_by_date": {k: v for k, v in sorted(resting_heart_rate_by_date.items())},
        "weight_kg_by_date": {k: v for k, v in sorted(weight_kg_by_date.items())},
        "body_age_by_date": {k: v for k, v in sorted(body_age_by_date.items())},
    }
    return health_overview, advanced, monthly, daily


def _build_numeric_change_block(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, dict[str, float | None]]:
    if not isinstance(previous, dict):
        return {}
    changes: dict[str, dict[str, float | None]] = {}
    for key, value in current.items():
        if not _is_number(value):
            continue
        prev_value = previous.get(key)
        if not _is_number(prev_value):
            continue
        delta = float(value) - float(prev_value)
        pct_change: float | None = None
        if float(prev_value) != 0.0:
            pct_change = round((delta / float(prev_value)) * 100.0, 3)
        changes[key] = {
            "delta": round(delta, 3),
            "pct_change": pct_change,
            "previous": round(float(prev_value), 3),
            "current": round(float(value), 3),
        }
    return changes


def _previous_report_path(report_root: Path, year: int) -> Path:
    return report_root / f"garmin_report_{year}" / "analyze" / "analyze_report_data.json"


def _load_previous_report(report_root: Path, year: int) -> dict[str, Any] | None:
    # Backward compatibility: also support previous location at year root.
    primary = _previous_report_path(report_root, year)
    legacy = report_root / f"garmin_report_{year}" / "analyze_report_data.json"
    candidate = primary if primary.exists() else legacy
    if not candidate.exists():
        return None
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _attach_year_over_year_changes(
    report: dict[str, Any],
    previous_report: dict[str, Any] | None,
    previous_year: int,
):
    meta = report.setdefault("meta", {})
    comparison_meta = {
        "previous_year": previous_year,
        "available": isinstance(previous_report, dict),
    }
    meta["previous_year_comparison"] = comparison_meta

    activity_curr = report.get("activity_overview")
    activity_prev = previous_report.get("activity_overview") if isinstance(previous_report, dict) else None
    if isinstance(activity_curr, dict):
        activity_curr["change_vs_previous_year"] = _build_numeric_change_block(activity_curr, activity_prev)

    health_curr = report.get("health_overview")
    health_prev = previous_report.get("health_overview") if isinstance(previous_report, dict) else None
    if isinstance(health_curr, dict):
        health_curr["change_vs_previous_year"] = _build_numeric_change_block(health_curr, health_prev)

    sports_curr = report.get("sports")
    sports_prev = previous_report.get("sports") if isinstance(previous_report, dict) else None
    if isinstance(sports_curr, dict):
        for sport_name, metrics in sports_curr.items():
            if not isinstance(metrics, dict):
                continue
            prev_metrics = sports_prev.get(sport_name) if isinstance(sports_prev, dict) else None
            metrics["change_vs_previous_year"] = _build_numeric_change_block(metrics, prev_metrics if isinstance(prev_metrics, dict) else None)

    advanced_curr = report.get("health_advanced")
    advanced_prev = previous_report.get("health_advanced") if isinstance(previous_report, dict) else None
    if isinstance(advanced_curr, dict):
        for key, metrics in advanced_curr.items():
            if not isinstance(metrics, dict):
                continue
            prev_metrics = advanced_prev.get(key) if isinstance(advanced_prev, dict) else None
            metrics["change_vs_previous_year"] = _build_numeric_change_block(metrics, prev_metrics if isinstance(prev_metrics, dict) else None)


def analyze_report_for_year(
    year: int,
    report_root: Path,
    strict: bool = False,
    include_previous_year_changes: bool = True,
) -> dict[str, Any]:
    report_dir = report_root / f"garmin_report_{year}"
    if not report_dir.exists():
        raise FileNotFoundError(f"report directory not found: {report_dir}")

    warnings: list[str] = []
    fallbacks_used: list[str] = []
    dropped_records = 0

    activities_source = _load_source(report_dir, "activities_workouts", "get_activities", warnings)
    user_summary_source = _load_source(report_dir, "daily_health_activity", "get_user_summary", warnings)
    sleep_source = _load_source(report_dir, "daily_health_activity", "get_sleep_data", warnings)
    hrv_source = _load_source(report_dir, "advanced_health_metrics", "get_hrv_data", warnings)
    stress_source = _load_source(report_dir, "daily_health_activity", "get_all_day_stress", warnings)
    respiration_source = _load_source(report_dir, "advanced_health_metrics", "get_respiration_data", warnings)
    weigh_in_source = _load_source(report_dir, "body_composition_weight", "get_daily_weigh_ins", warnings)

    if not user_summary_source["records"]:
        stats_fallback = _load_source(report_dir, "daily_health_activity", "get_stats_and_body", warnings)
        if stats_fallback["records"]:
            user_summary_source = stats_fallback
            fallbacks_used.append("user_summary<-get_stats_and_body")

    core_missing = []
    if not activities_source["records"]:
        core_missing.append("get_activities")
    if not user_summary_source["records"]:
        core_missing.append("get_user_summary")
    if not sleep_source["records"]:
        core_missing.append("get_sleep_data")
    if strict and core_missing:
        raise RuntimeError(f"missing required core sources: {', '.join(core_missing)}")
    if core_missing:
        warnings.append(f"missing core sources: {', '.join(core_missing)}")

    sources = [
        activities_source,
        user_summary_source,
        sleep_source,
        hrv_source,
        stress_source,
        respiration_source,
        weigh_in_source,
    ]
    dropped_records = int(sum(int(src.get("dropped", 0)) for src in sources))

    activity_overview, sports, activity_monthly, activity_daily = _analyze_activities(activities_source["records"])
    health_overview, health_advanced, health_monthly, health_daily = _analyze_health(
        year=year,
        user_summary_rows=user_summary_source["records"],
        sleep_rows=sleep_source["records"],
        hrv_rows=hrv_source["records"],
        stress_rows=stress_source["records"],
        respiration_rows=respiration_source["records"],
        weigh_in_rows=weigh_in_source["records"],
    )

    result = {
        "meta": {
            "year": year,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "schema_version": "1.0",
            "input_data_root": str((report_dir / "data").resolve()),
            "sources": [
                {
                    "method": src["method"],
                    "section": src["section"],
                    "path": src["path"],
                    "exists": src["exists"],
                    "status": src["status"],
                    "records_used": len(src["records"]),
                }
                for src in sources
            ],
        },
        "activity_overview": activity_overview,
        "sports": sports,
        "health_overview": health_overview,
        "health_advanced": health_advanced,
        "monthly_trends": {
            "activity_count_by_month": activity_monthly["activity_count_by_month"],
            "distance_m_by_month": activity_monthly["distance_m_by_month"],
            "steps_by_month": health_monthly["steps_by_month"],
            "sleep_hours_by_month": health_monthly["sleep_hours_by_month"],
        },
        "daily_trends": {
            "duration_h_by_date": activity_daily["duration_h_by_date"],
            "calories_by_date": activity_daily["calories_by_date"],
            "intensity_minutes_by_date": health_daily["intensity_minutes_by_date"],
            "resting_heart_rate_by_date": health_daily["resting_heart_rate_by_date"],
            "weight_kg_by_date": health_daily["weight_kg_by_date"],
            "body_age_by_date": health_daily["body_age_by_date"],
        },
        "quality": {
            "warnings": warnings,
            "dropped_records": dropped_records,
            "fallbacks_used": fallbacks_used,
        },
    }
    if include_previous_year_changes:
        previous_year = year - 1
        previous_report = _load_previous_report(report_root=report_root, year=previous_year)
        if previous_report is None:
            previous_dir = report_root / f"garmin_report_{previous_year}"
            if previous_dir.exists():
                try:
                    # Build comparison baseline directly from previous year's raw data when cached analyze output is absent.
                    previous_report = analyze_report_for_year(
                        year=previous_year,
                        report_root=report_root,
                        strict=False,
                        include_previous_year_changes=False,
                    )
                except Exception as exc:
                    warnings.append(f"failed to build previous-year baseline: {exc}")
        _attach_year_over_year_changes(report=result, previous_report=previous_report, previous_year=previous_year)
    else:
        _attach_year_over_year_changes(report=result, previous_report=None, previous_year=year - 1)
    return result


def write_analyze_report(year: int, report_root: Path, data: dict[str, Any], pretty: bool = True) -> Path:
    report_dir = report_root / f"garmin_report_{year}"
    output_path = report_dir / "analyze" / "analyze_report_data.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    indent = 2 if pretty else None
    text = json.dumps(data, ensure_ascii=False, indent=indent)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate yearly analyze_report_data.json from Garmin classified data")
    parser.add_argument("--year", type=int, required=True, help="report year, e.g. 2024")
    parser.add_argument("--report-root", default=".", help="root directory containing garmin_report_<year>")
    parser.add_argument("--strict", action="store_true", help="fail if required core sources are missing")
    parser.add_argument("--pretty", dest="pretty", action="store_true", help="write pretty JSON output (default)")
    parser.add_argument("--no-pretty", dest="pretty", action="store_false", help="write compact JSON output")
    parser.set_defaults(pretty=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_root = Path(args.report_root)
    try:
        report = analyze_report_for_year(year=args.year, report_root=report_root, strict=args.strict)
        output = write_analyze_report(year=args.year, report_root=report_root, data=report, pretty=args.pretty)
    except Exception as exc:
        print(f"❌ 分析失败: {exc}")
        return 2

    print(f"✓ 分析完成: {output}")
    print(f"  活动总数: {report['activity_overview']['total_activities']}")
    print(f"  总步数: {report['health_overview']['total_steps']}")
    print(f"  质量告警: {len(report['quality']['warnings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
