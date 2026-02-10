import json
import tempfile
import unittest
from pathlib import Path

from analyze_report_data import (
    analyze_report_for_year,
    flatten_envelope_responses,
    pace_min_per_100m,
    pace_min_per_km,
    resolve_method_file,
    write_analyze_report,
)


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _envelope(method: str, section: str, responses: list, status: str = "success"):
    return {
        "method": method,
        "section": section,
        "year": 2024,
        "call_type": "daily",
        "status": status,
        "request_args": [{"i": i} for i in range(len(responses))],
        "data": [{"request": {"i": i}, "response": r} for i, r in enumerate(responses)],
        "errors": [],
        "stats": {
            "attempted_calls": len(responses),
            "success_calls": len(responses),
            "failed_calls": 0,
            "duration_seconds": 0.0,
        },
    }


class AnalyzeReportDataTests(unittest.TestCase):
    def test_resolve_method_file_supports_new_and_old_layout(self):
        with tempfile.TemporaryDirectory() as td:
            report_dir = Path(td) / "garmin_report_2024"
            new_path = report_dir / "data" / "activities_workouts" / "get_activities.json"
            old_path = report_dir / "data" / "classified" / "activities_workouts" / "get_activities.json"

            _write_json(new_path, _envelope("get_activities", "Activities & Workouts", [[]]))
            p = resolve_method_file(report_dir, "activities_workouts", "get_activities")
            self.assertEqual(p, new_path)

            new_path.unlink()
            _write_json(old_path, _envelope("get_activities", "Activities & Workouts", [[]]))
            p2 = resolve_method_file(report_dir, "activities_workouts", "get_activities")
            self.assertEqual(p2, old_path)

    def test_flatten_envelope_responses_flattens_lists_and_dicts(self):
        payload = _envelope(
            "get_activities",
            "Activities & Workouts",
            responses=[
                [{"activityId": 1}, {"activityId": 2}],
                {"activityId": 3},
                None,
            ],
        )
        rows = flatten_envelope_responses(payload)
        self.assertEqual(len(rows), 3)
        self.assertEqual([r.get("activityId") for r in rows], [1, 2, 3])

    def test_pace_helpers_handle_zero_distance(self):
        self.assertIsNone(pace_min_per_km(0, 3600))
        self.assertIsNone(pace_min_per_100m(0, 3600))
        self.assertAlmostEqual(pace_min_per_km(10000, 3000), 5.0)
        self.assertAlmostEqual(pace_min_per_100m(1500, 1800), 2.0)

    def test_analyze_report_for_year_computes_sports_and_sleep_filters(self):
        with tempfile.TemporaryDirectory() as td:
            report_dir = Path(td) / "garmin_report_2024"
            data_dir = report_dir / "data"
            activities = [
                {
                    "activityId": 1,
                    "activityName": "Run A",
                    "startTimeLocal": "2024-01-03 07:00:00",
                    "activityType": {"typeKey": "running"},
                    "distance": 10000.0,
                    "duration": 3000.0,
                    "calories": 600.0,
                    "elevationGain": 50.0,
                    "averageHR": 150.0,
                },
                {
                    "activityId": 2,
                    "activityName": "Strength A",
                    "startTimeLocal": "2024-01-04 19:00:00",
                    "activityType": {"typeKey": "strength_training"},
                    "distance": 0.0,
                    "duration": 1800.0,
                    "calories": 300.0,
                    "totalSets": 10,
                    "totalReps": 120,
                    "averageHR": 120.0,
                },
            ]
            user_summary = [
                {
                    "calendarDate": "2024-01-03",
                    "totalSteps": 10000,
                    "totalDistanceMeters": 7000,
                    "activeKilocalories": 500,
                    "moderateIntensityMinutes": 30,
                    "vigorousIntensityMinutes": 15,
                    "restingHeartRate": 45,
                },
                {
                    "calendarDate": "2024-01-04",
                    "totalSteps": 5000,
                    "totalDistanceMeters": 3500,
                    "activeKilocalories": 200,
                    "moderateIntensityMinutes": 10,
                    "vigorousIntensityMinutes": 0,
                    "restingHeartRate": 47,
                },
            ]
            sleep = [
                {
                    "dailySleepDTO": {
                        "calendarDate": "2024-01-03",
                        "sleepTimeSeconds": 28800,
                        "deepSleepSeconds": 3600,
                        "lightSleepSeconds": 18000,
                        "remSleepSeconds": 7200,
                        "sleepScores": {"overall": {"value": 80}},
                    }
                },
                {
                    "dailySleepDTO": {
                        "calendarDate": "2024-01-04",
                        "sleepTimeSeconds": 0,
                        "deepSleepSeconds": 0,
                        "lightSleepSeconds": 0,
                        "remSleepSeconds": 0,
                        "sleepScores": {"overall": {"value": 60}},
                    }
                },
            ]
            hrv = [
                {"hrvSummary": {"calendarDate": "2024-01-03", "lastNightAvg": None, "weeklyAvg": 60}},
                {"hrvSummary": {"calendarDate": "2024-01-04", "lastNightAvg": 70, "weeklyAvg": 62}},
            ]
            stress = [
                {"calendarDate": "2024-01-03", "avgStressLevel": 20, "maxStressLevel": 80},
                {"calendarDate": "2024-01-04", "avgStressLevel": 30, "maxStressLevel": 90},
            ]
            respiration = [
                {"calendarDate": "2024-01-03", "avgSleepRespirationValue": 13.5},
                {"calendarDate": "2024-01-04", "avgSleepRespirationValue": 14.5},
            ]
            weigh_ins = [
                {
                    "startDate": "2024-01-03",
                    "endDate": "2024-01-03",
                    "dateWeightList": [
                        {
                            "calendarDate": "2024-01-03",
                            "weight": 74100.0,
                            "metabolicAge": 35,
                        }
                    ],
                },
                {
                    "startDate": "2024-01-04",
                    "endDate": "2024-01-04",
                    "dateWeightList": [
                        {
                            "calendarDate": "2024-01-04",
                            "weight": 73900.0,
                            "metabolicAge": 34,
                        }
                    ],
                },
            ]

            _write_json(
                data_dir / "activities_workouts" / "get_activities.json",
                _envelope("get_activities", "Activities & Workouts", [activities], status="success"),
            )
            _write_json(
                data_dir / "daily_health_activity" / "get_user_summary.json",
                _envelope("get_user_summary", "Daily Health & Activity", user_summary, status="success"),
            )
            _write_json(
                data_dir / "daily_health_activity" / "get_sleep_data.json",
                _envelope("get_sleep_data", "Daily Health & Activity", sleep, status="success"),
            )
            _write_json(
                data_dir / "advanced_health_metrics" / "get_hrv_data.json",
                _envelope("get_hrv_data", "Advanced Health Metrics", hrv, status="success"),
            )
            _write_json(
                data_dir / "daily_health_activity" / "get_all_day_stress.json",
                _envelope("get_all_day_stress", "Daily Health & Activity", stress, status="success"),
            )
            _write_json(
                data_dir / "advanced_health_metrics" / "get_respiration_data.json",
                _envelope("get_respiration_data", "Advanced Health Metrics", respiration, status="success"),
            )
            _write_json(
                data_dir / "body_composition_weight" / "get_daily_weigh_ins.json",
                _envelope("get_daily_weigh_ins", "Body Composition & Weight", weigh_ins, status="success"),
            )

            report = analyze_report_for_year(year=2024, report_root=Path(td), strict=True)

            self.assertEqual(report["activity_overview"]["total_activities"], 2)
            self.assertEqual(report["sports"]["running"]["count"], 1)
            self.assertEqual(report["sports"]["strength_training"]["total_sets"], 10)
            self.assertEqual(report["health_overview"]["sleep_recorded_days"], 1)
            self.assertEqual(report["health_overview"]["avg_sleep_score"], 80.0)
            self.assertEqual(report["health_overview"]["avg_daily_intensity_minutes"], 35.0)
            self.assertEqual(report["health_advanced"]["hrv"]["avg"], 65.0)
            self.assertAlmostEqual(report["sports"]["running"]["avg_pace_min_per_km"], 5.0)
            self.assertNotIn("spo2", report["health_advanced"])
            self.assertIn("change_vs_previous_year", report["activity_overview"])
            self.assertIn("top_activities_by_duration", report["activity_overview"])
            self.assertEqual(len(report["activity_overview"]["top_activities_by_duration"]), 2)
            self.assertIn("top_activities_by_duration", report["sports"]["running"])
            self.assertEqual(len(report["sports"]["running"]["top_activities_by_duration"]), 1)
            self.assertIn("daily_trends", report)
            self.assertIn("duration_h_by_date", report["daily_trends"])
            self.assertIn("calories_by_date", report["daily_trends"])
            self.assertIn("intensity_minutes_by_date", report["daily_trends"])
            self.assertIn("resting_heart_rate_by_date", report["daily_trends"])
            self.assertIn("weight_kg_by_date", report["daily_trends"])
            self.assertIn("body_age_by_date", report["daily_trends"])
            self.assertAlmostEqual(report["daily_trends"]["duration_h_by_date"]["2024-01-03"], 0.833, places=3)
            self.assertAlmostEqual(report["daily_trends"]["calories_by_date"]["2024-01-04"], 300.0, places=3)
            self.assertAlmostEqual(report["daily_trends"]["intensity_minutes_by_date"]["2024-01-03"], 60.0, places=3)
            self.assertAlmostEqual(report["daily_trends"]["resting_heart_rate_by_date"]["2024-01-03"], 45.0, places=3)
            self.assertAlmostEqual(report["daily_trends"]["weight_kg_by_date"]["2024-01-03"], 74.1, places=3)
            self.assertAlmostEqual(report["daily_trends"]["body_age_by_date"]["2024-01-03"], 35.0, places=3)
            self.assertIn("sport_type_analysis", report["sports"])
            sport_type_analysis = report["sports"]["sport_type_analysis"]
            self.assertIn("by_count", sport_type_analysis)
            self.assertIn("by_duration_s", sport_type_analysis)
            self.assertIn("by_calories", sport_type_analysis)
            self.assertIn("by_distance_m", sport_type_analysis)
            self.assertIn("display_names_zh", sport_type_analysis)
            self.assertEqual(sport_type_analysis["by_distance_m"]["running"], 10000.0)
            self.assertEqual(sport_type_analysis["display_names_zh"]["running"], "跑步")

    def test_analyze_report_for_2024_real_data_contains_required_sections(self):
        report = analyze_report_for_year(year=2024, report_root=Path("."), strict=False)
        self.assertIn("meta", report)
        self.assertIn("activity_overview", report)
        self.assertIn("sports", report)
        self.assertIn("health_overview", report)
        self.assertIn("health_advanced", report)
        self.assertIn("monthly_trends", report)
        self.assertIn("quality", report)
        self.assertGreater(report["health_overview"]["total_steps"], 0)
        self.assertNotIn("spo2", report["health_advanced"])
        self.assertIsInstance(report["quality"]["warnings"], list)

    def test_write_analyze_report_writes_into_analyze_subdir(self):
        with tempfile.TemporaryDirectory() as td:
            report_root = Path(td)
            report_dir = report_root / "garmin_report_2024"
            report_dir.mkdir(parents=True, exist_ok=True)
            output = write_analyze_report(
                year=2024,
                report_root=report_root,
                data={"meta": {"year": 2024}},
                pretty=True,
            )
            self.assertEqual(output, report_dir / "analyze" / "analyze_report_data.json")
            self.assertTrue(output.exists())

    def test_analyze_report_includes_previous_year_changes_when_available(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report_dir = root / "garmin_report_2024"
            data_dir = report_dir / "data"
            prev_output = root / "garmin_report_2023" / "analyze" / "analyze_report_data.json"

            _write_json(
                prev_output,
                {
                    "activity_overview": {"total_activities": 1},
                    "health_overview": {"total_steps": 1000},
                    "sports": {"running": {"count": 1}},
                    "health_advanced": {"hrv": {"avg": 60}},
                },
            )

            activities = [{
                "activityId": 1,
                "activityName": "Run A",
                "startTimeLocal": "2024-01-03 07:00:00",
                "activityType": {"typeKey": "running"},
                "distance": 1000.0,
                "duration": 300.0,
                "calories": 100.0,
                "averageHR": 130.0,
            }]
            _write_json(
                data_dir / "activities_workouts" / "get_activities.json",
                _envelope("get_activities", "Activities & Workouts", [activities], status="success"),
            )
            _write_json(
                data_dir / "daily_health_activity" / "get_user_summary.json",
                _envelope("get_user_summary", "Daily Health & Activity", [{"calendarDate": "2024-01-03", "totalSteps": 1500}], status="success"),
            )
            _write_json(
                data_dir / "daily_health_activity" / "get_sleep_data.json",
                _envelope("get_sleep_data", "Daily Health & Activity", [{"dailySleepDTO": {"calendarDate": "2024-01-03", "sleepTimeSeconds": 3600, "deepSleepSeconds": 600, "lightSleepSeconds": 1800, "remSleepSeconds": 1200}}], status="success"),
            )
            _write_json(
                data_dir / "advanced_health_metrics" / "get_hrv_data.json",
                _envelope("get_hrv_data", "Advanced Health Metrics", [{"hrvSummary": {"calendarDate": "2024-01-03", "weeklyAvg": 70}}], status="success"),
            )
            _write_json(
                data_dir / "daily_health_activity" / "get_all_day_stress.json",
                _envelope("get_all_day_stress", "Daily Health & Activity", [{"calendarDate": "2024-01-03", "avgStressLevel": 20, "maxStressLevel": 50}], status="success"),
            )
            _write_json(
                data_dir / "advanced_health_metrics" / "get_respiration_data.json",
                _envelope("get_respiration_data", "Advanced Health Metrics", [{"calendarDate": "2024-01-03", "avgSleepRespirationValue": 14.0}], status="success"),
            )

            report = analyze_report_for_year(year=2024, report_root=root, strict=True)
            self.assertTrue(report["meta"]["previous_year_comparison"]["available"])
            self.assertIn("total_steps", report["health_overview"]["change_vs_previous_year"])
            self.assertIn("count", report["sports"]["running"]["change_vs_previous_year"])


if __name__ == "__main__":
    unittest.main()
