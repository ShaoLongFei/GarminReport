import base64
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from fetch_garmin_data import (
    build_calls_for_method,
    classify_call_type,
    collect_year_data,
    get_completed_request_keys,
    iter_year_dates,
    parse_api_reference,
    request_key,
    serialize_response_data,
)


class FetchGarminDataTests(unittest.TestCase):
    def test_parse_api_reference_finds_88_methods(self):
        methods = parse_api_reference(Path("docs/python-garminconnect-pull-api-detailed.md"))
        self.assertEqual(len(methods), 88)

        by_name = {m["method"]: m for m in methods}
        self.assertIn("get_full_name", by_name)
        self.assertIn("get_activities", by_name)
        self.assertIn("download_activity", by_name)

        self.assertEqual(by_name["get_full_name"]["section_slug"], "user_profile")
        self.assertEqual(by_name["get_activities"]["section_slug"], "activities_workouts")

    def test_classify_call_type(self):
        self.assertEqual(classify_call_type("get_full_name", "get_full_name()"), "noarg")
        self.assertEqual(classify_call_type("get_sleep_data", "get_sleep_data(cdate)"), "daily")
        self.assertEqual(
            classify_call_type("get_blood_pressure", "get_blood_pressure(startdate, enddate=None)"),
            "date_range",
        )
        self.assertEqual(
            classify_call_type("get_activities", "get_activities(start=0, limit=20, activitytype=None)"),
            "paged",
        )
        self.assertEqual(
            classify_call_type("get_activity", "get_activity(activity_id)"),
            "id_based",
        )
        self.assertEqual(
            classify_call_type(
                "download_activity",
                "download_activity(activity_id, dl_fmt=ActivityDownloadFormat.TCX)",
            ),
            "download",
        )
        self.assertEqual(
            classify_call_type("get_weekly_steps", "get_weekly_steps(end, weeks=52)"),
            "weekly",
        )
        self.assertEqual(
            classify_call_type(
                "get_lactate_threshold",
                "get_lactate_threshold(latest=True, start_date=None, end_date=None, aggregation='daily')",
            ),
            "special",
        )

    def test_build_calls_for_weekly_uses_52_weeks(self):
        ctx = {
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "dates": [],
        }
        calls, skip = build_calls_for_method(
            "get_weekly_steps",
            "get_weekly_steps(end, weeks=52)",
            "weekly",
            ctx,
            include_downloads=True,
        )
        self.assertIsNone(skip)
        self.assertEqual(calls, [{"end": "2023-12-31", "weeks": 52}])

    def test_build_calls_for_body_battery_chunks_date_range(self):
        ctx = {
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "dates": [],
        }
        calls, skip = build_calls_for_method(
            "get_body_battery",
            "get_body_battery(startdate, enddate=None)",
            "date_range",
            ctx,
            include_downloads=True,
        )
        self.assertIsNone(skip)
        self.assertGreater(len(calls), 1)
        self.assertEqual(calls[0], {"startdate": "2023-01-01", "enddate": "2023-01-31"})
        self.assertEqual(calls[-1]["enddate"], "2023-12-31")

    def test_iter_year_dates_includes_leap_day(self):
        dates = list(iter_year_dates(2024))
        self.assertEqual(len(dates), 366)
        self.assertEqual(dates[0], "2024-01-01")
        self.assertEqual(dates[-1], "2024-12-31")
        self.assertIn("2024-02-29", dates)

    def test_serialize_response_data_bytes(self):
        payload = b"abc"
        encoded = serialize_response_data(payload)

        self.assertEqual(encoded["encoding"], "base64")
        self.assertEqual(encoded["byte_length"], 3)
        self.assertEqual(encoded["data_base64"], base64.b64encode(payload).decode("ascii"))
        self.assertEqual(encoded["sha256"], hashlib.sha256(payload).hexdigest())

    def test_collect_year_data_writes_manifest_and_skips_download_when_disabled(self):
        class FakeClient:
            def get_activities(self, start=0, limit=20, activitytype=None):
                return []

            def get_workouts(self, start=0, limit=100):
                return {"workouts": []}

            def get_devices(self):
                return []

            def get_user_profile(self):
                return {"userProfileNumber": 123}

            def get_device_last_used(self):
                return {}

            def get_gear(self, userProfileNumber):
                return []

            def get_training_plans(self):
                return {"trainingPlanList": []}

            def get_full_name(self):
                return "tester"

            def get_sleep_data(self, cdate):
                return {"calendarDate": cdate, "sleepTimeSeconds": 1}

        methods = [
            {
                "section": "User & Profile",
                "section_slug": "user_profile",
                "method": "get_full_name",
                "signature": "get_full_name()",
            },
            {
                "section": "Training Plans",
                "section_slug": "training_plans",
                "method": "get_training_plans",
                "signature": "get_training_plans()",
            },
            {
                "section": "Activities & Workouts",
                "section_slug": "activities_workouts",
                "method": "download_activity",
                "signature": "download_activity(activity_id, dl_fmt=ActivityDownloadFormat.TCX)",
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            manifest_path = collect_year_data(
                client=FakeClient(),
                methods=methods,
                year=2025,
                output_root=Path(td),
                overwrite=True,
                include_downloads=False,
                selected_sections=None,
            )
            self.assertTrue(manifest_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["total_methods"], 3)
            by_method = {m["method"]: m for m in manifest["methods"]}
            self.assertEqual(by_method["get_full_name"]["status"], "success")
            self.assertEqual(by_method["get_training_plans"]["status"], "success")
            self.assertEqual(by_method["download_activity"]["status"], "skipped")

    def test_get_completed_request_keys_and_request_key(self):
        envelope = {
            "data": [
                {"request": {"cdate": "2025-01-01"}, "response": {"ok": 1}},
                {"request": {"cdate": "2025-01-02"}, "response": {"ok": 1}},
                {"response": {"ignored": True}},
            ]
        }
        completed = get_completed_request_keys(envelope)
        self.assertIn(request_key({"cdate": "2025-01-01"}), completed)
        self.assertIn(request_key({"cdate": "2025-01-02"}), completed)
        self.assertEqual(len(completed), 2)

    def test_collect_year_data_resumes_and_skips_success_method(self):
        class FakeClient:
            def __init__(self):
                self.calls = 0

            def get_activities(self, start=0, limit=20, activitytype=None):
                return []

            def get_workouts(self, start=0, limit=100):
                return {"workouts": []}

            def get_devices(self):
                return []

            def get_user_profile(self):
                return {"userProfileNumber": 123}

            def get_device_last_used(self):
                return {}

            def get_gear(self, userProfileNumber):
                return []

            def get_training_plans(self):
                return {"trainingPlanList": []}

            def get_full_name(self):
                self.calls += 1
                return "tester"

        methods = [
            {
                "section": "User & Profile",
                "section_slug": "user_profile",
                "method": "get_full_name",
                "signature": "get_full_name()",
            }
        ]

        with tempfile.TemporaryDirectory() as td:
            client = FakeClient()
            collect_year_data(
                client=client,
                methods=methods,
                year=2025,
                output_root=Path(td),
                overwrite=False,
                include_downloads=False,
                selected_sections=None,
            )
            first_calls = client.calls
            self.assertEqual(first_calls, 1)

            collect_year_data(
                client=client,
                methods=methods,
                year=2025,
                output_root=Path(td),
                overwrite=False,
                include_downloads=False,
                selected_sections=None,
            )
            self.assertEqual(client.calls, first_calls)

    def test_collect_year_data_excludes_known_duplicate_methods(self):
        class FakeClient:
            def __init__(self):
                self.stats_calls = 0
                self.stress_calls = 0
                self.activities_by_date_calls = 0
                self.full_name_calls = 0

            def get_activities(self, start=0, limit=20, activitytype=None):
                return []

            def get_workouts(self, start=0, limit=100):
                return {"workouts": []}

            def get_devices(self):
                return []

            def get_user_profile(self):
                return {"userProfileNumber": 123}

            def get_device_last_used(self):
                return {}

            def get_gear(self, userProfileNumber):
                return []

            def get_training_plans(self):
                return {"trainingPlanList": []}

            def get_stats(self, cdate):
                self.stats_calls += 1
                return {"calendarDate": cdate}

            def get_stress_data(self, cdate):
                self.stress_calls += 1
                return {"calendarDate": cdate}

            def get_activities_by_date(self, startdate, enddate=None, activitytype=None, sortorder=None):
                self.activities_by_date_calls += 1
                return []

            def get_full_name(self):
                self.full_name_calls += 1
                return "tester"

        methods = [
            {
                "section": "Daily Health & Activity",
                "section_slug": "daily_health_activity",
                "method": "get_stats",
                "signature": "get_stats(cdate)",
            },
            {
                "section": "Advanced Health Metrics",
                "section_slug": "advanced_health_metrics",
                "method": "get_stress_data",
                "signature": "get_stress_data(cdate)",
            },
            {
                "section": "Activities & Workouts",
                "section_slug": "activities_workouts",
                "method": "get_activities_by_date",
                "signature": "get_activities_by_date(startdate, enddate=None, activitytype=None, sortorder=None)",
            },
            {
                "section": "User & Profile",
                "section_slug": "user_profile",
                "method": "get_full_name",
                "signature": "get_full_name()",
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            client = FakeClient()
            manifest_path = collect_year_data(
                client=client,
                methods=methods,
                year=2025,
                output_root=Path(td),
                overwrite=True,
                include_downloads=False,
                selected_sections=None,
            )

            self.assertEqual(client.stats_calls, 0)
            self.assertEqual(client.stress_calls, 0)
            self.assertEqual(client.activities_by_date_calls, 0)
            self.assertEqual(client.full_name_calls, 1)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            names = {m["method"] for m in manifest["methods"]}
            self.assertNotIn("get_stats", names)
            self.assertNotIn("get_stress_data", names)
            self.assertNotIn("get_activities_by_date", names)
            self.assertIn("get_full_name", names)

    def test_collect_year_data_supports_parallel_methods(self):
        class FakeClient:
            def __init__(self):
                self.lock = threading.Lock()
                self.inflight = 0
                self.max_inflight = 0
                self.full_name_calls = 0
                self.unit_system_calls = 0

            def _track(self):
                with self.lock:
                    self.inflight += 1
                    if self.inflight > self.max_inflight:
                        self.max_inflight = self.inflight
                time.sleep(0.05)
                with self.lock:
                    self.inflight -= 1

            def get_activities(self, start=0, limit=20, activitytype=None):
                return []

            def get_workouts(self, start=0, limit=100):
                return {"workouts": []}

            def get_devices(self):
                return []

            def get_user_profile(self):
                return {"userProfileNumber": 123}

            def get_device_last_used(self):
                return {}

            def get_gear(self, userProfileNumber):
                return []

            def get_training_plans(self):
                return {"trainingPlanList": []}

            def get_full_name(self):
                self._track()
                self.full_name_calls += 1
                return "tester"

            def get_unit_system(self):
                self._track()
                self.unit_system_calls += 1
                return {"unit": "metric"}

        methods = [
            {
                "section": "User & Profile",
                "section_slug": "user_profile",
                "method": "get_full_name",
                "signature": "get_full_name()",
            },
            {
                "section": "User & Profile",
                "section_slug": "user_profile",
                "method": "get_unit_system",
                "signature": "get_unit_system()",
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            client = FakeClient()
            manifest_path = collect_year_data(
                client=client,
                methods=methods,
                year=2025,
                output_root=Path(td),
                overwrite=True,
                include_downloads=False,
                selected_sections=None,
                max_workers=2,
            )

            self.assertEqual(client.full_name_calls, 1)
            self.assertEqual(client.unit_system_calls, 1)
            self.assertGreaterEqual(client.max_inflight, 2)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["total_methods"], 2)


if __name__ == "__main__":
    unittest.main()
