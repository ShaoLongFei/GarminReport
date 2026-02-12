import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import generate_report as report_module

from generate_report import (
    build_html_report_from_analysis,
    load_analysis_report,
    load_redesign_report_css,
    load_redesign_report_js,
    load_redesign_report_template,
)


class GenerateReportAnalysisLoadTests(unittest.TestCase):
    def test_load_redesign_report_template_contains_placeholders(self):
        template = load_redesign_report_template()
        self.assertIn("__YEAR__", template)
        self.assertIn("__REPORT_DATA_JSON__", template)
        self.assertIn("__REPORT_CSS__", template)
        self.assertIn("__REPORT_JS__", template)
        self.assertIn("iso-view-btn", template)

    def test_load_redesign_report_css_contains_core_selectors(self):
        css = load_redesign_report_css()
        self.assertIn(".report-shell", css)
        self.assertIn(".iso-view-switch", css)
        self.assertIn('.iso-stage[data-iso-view-mode="both"]', css)
        self.assertIn("repeat(3, minmax(180px, 1.1fr))", css)
        self.assertIn(".compare-row .compare-cell {", css)

    def test_load_redesign_report_js_contains_core_behaviors(self):
        js = load_redesign_report_js()
        self.assertIn("setIsoViewMode", js)
        self.assertIn("ensureSports3DContributionCharts", js)
        self.assertIn("window.print()", js)
        self.assertIn("stage.setAttribute('data-iso-view-mode', isoViewMode);", js)
        self.assertIn("if (!hasBodyAgeData)", js)
        self.assertIn("bodyAgePanel.remove();", js)
        self.assertIn("function computeSeriesRange(values, options)", js)

    def test_template_loader_missing_file_raises_clear_error(self):
        missing = Path("/tmp/garmin-report-missing-template.html")
        report_module.load_redesign_report_template.cache_clear()
        with patch.object(report_module, "REDESIGN_TEMPLATE_PATH", missing):
            with self.assertRaises(FileNotFoundError) as ctx:
                report_module.load_redesign_report_template()
        report_module.load_redesign_report_template.cache_clear()
        self.assertIn("报告模板不存在", str(ctx.exception))
        self.assertIn(str(missing), str(ctx.exception))

    def test_css_loader_missing_file_raises_clear_error(self):
        missing = Path("/tmp/garmin-report-missing-style.css")
        report_module.load_redesign_report_css.cache_clear()
        with patch.object(report_module, "REDESIGN_CSS_PATH", missing):
            with self.assertRaises(FileNotFoundError) as ctx:
                report_module.load_redesign_report_css()
        report_module.load_redesign_report_css.cache_clear()
        self.assertIn("报告样式不存在", str(ctx.exception))
        self.assertIn(str(missing), str(ctx.exception))

    def test_summarize_totals_from_analysis(self):
        totals = report_module.summarize_totals_from_analysis({
            "activity_overview": {
                "total_activities": 12,
                "total_distance_m": 24500.5,
                "total_duration_s": 7320,
            }
        })
        self.assertEqual(totals[0], 12)
        self.assertAlmostEqual(totals[1], 24.5005, places=6)
        self.assertAlmostEqual(totals[2], 2.0333333333, places=6)

    def test_prefers_analyze_subdir_file(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "garmin_report_2025"
            analyze_path = data_dir / "analyze" / "analyze_report_data.json"
            analyze_path.parent.mkdir(parents=True, exist_ok=True)
            analyze_path.write_text(json.dumps({"meta": {"year": 2025}}), encoding="utf-8")

            payload, path = load_analysis_report(data_dir=data_dir)
            self.assertEqual(payload["meta"]["year"], 2025)
            self.assertEqual(path, analyze_path)

    def test_falls_back_to_legacy_root_file(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "garmin_report_2024"
            legacy = data_dir / "analyze_report_data.json"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_text(json.dumps({"meta": {"year": 2024}}), encoding="utf-8")

            payload, path = load_analysis_report(data_dir=data_dir)
            self.assertEqual(payload["meta"]["year"], 2024)
            self.assertEqual(path, legacy)

    def test_report_from_analysis_contains_redesigned_dark_dashboard_payload(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report_2025.html"
            analysis_data = {
                "activity_overview": {
                    "total_activities": 2,
                    "total_distance_m": 18000,
                    "total_duration_s": 7200,
                    "total_calories": 500,
                    "total_elevation_gain_m": 20,
                    "change_vs_previous_year": {
                        "total_distance_m": {"current": 18000, "previous": 21000, "pct_change": -14.286},
                    },
                    "top_activities_by_duration": [
                        {
                            "date": "2025-01-01",
                            "type_key": "running",
                            "activity_name": "Run",
                            "distance_m": 10000,
                            "duration_s": 3600,
                        }
                    ],
                },
                "health_overview": {
                    "sleep_recorded_days": 10,
                    "avg_sleep_hours": 7.2,
                    "avg_sleep_score": 78.4,
                    "avg_deep_sleep_hours": 1.4,
                    "total_steps": 120000,
                    "avg_daily_steps": 8000,
                    "avg_daily_intensity_minutes": 32.5,
                    "total_intensity_minutes": 12000,
                    "change_vs_previous_year": {
                        "avg_daily_steps": {"current": 8000, "previous": 9000, "pct_change": -11.111},
                    },
                },
                "health_advanced": {"hrv": {"days": 9}},
                "sports": {
                    "running": {
                        "count": 1,
                        "total_distance_m": 10000,
                        "total_duration_s": 3600,
                        "avg_pace_min_per_km": 6.0,
                        "top_activities_by_duration": [],
                    },
                    "swimming": {
                        "count": 1,
                        "total_distance_m": 1000,
                        "total_duration_s": 1920,
                        "avg_pace_min_per_100m": 3.2,
                        "top_activities_by_duration": [],
                    },
                    "sport_type_distribution": {"running": 1, "swimming": 1},
                    "sport_type_duration_s_distribution": {"running": 3600, "swimming": 1920},
                    "sport_type_calories_distribution": {"running": 300, "swimming": 200},
                    "sport_type_distance_m_distribution": {"running": 10000, "swimming": 1000},
                    "sport_type_analysis": {
                        "display_names_zh": {"running": "跑步", "swimming": "游泳"},
                    },
                },
                "monthly_trends": {
                    "distance_m_by_month": {"01": 10000},
                    "activity_count_by_month": {"01": 2},
                    "steps_by_month": {"01": 20000},
                    "sleep_hours_by_month": {"01": 200},
                },
                "daily_trends": {
                    "duration_h_by_date": {"2025-01-01": 1.0},
                    "calories_by_date": {"2025-01-01": 300},
                },
                "meta": {"year": 2025},
            }

            build_html_report_from_analysis(analysis_data, out_path=out, year=2025)
            html = out.read_text(encoding="utf-8")

            self.assertIn("window.REPORT_DATA =", html)
            self.assertIn("https://cdn.jsdelivr.net/npm/echarts", html)
            self.assertIn("https://cdn.jsdelivr.net/npm/echarts-gl", html)
            self.assertIn("概览总览", html)
            self.assertIn("运动分析", html)
            self.assertIn("健康洞察", html)
            self.assertIn("年度对比", html)
            self.assertIn("id=\"btn-export-pdf\"", html)
            self.assertIn("分享 / 打印 PDF", html)
            self.assertIn("@page", html)
            self.assertIn("window.print()", html)
            self.assertIn("beforeprint", html)
            self.assertIn("afterprint", html)
            self.assertIn("printPreview", html)
            self.assertIn("background: #070b16;", html)
            self.assertIn("color: var(--text-main);", html)
            self.assertNotIn("color: #000;", html)
            self.assertIn("id=\"share-toast\"", html)
            self.assertIn("navigator.share", html)
            self.assertIn("ensureTabCharts", html)
            self.assertIn("requestAnimationFrame", html)
            self.assertIn("URLSearchParams(window.location.search)", html)
            self.assertIn("history.replaceState", html)
            self.assertIn("renderedTabs", html)
            self.assertIn("const isMobile = window.matchMedia('(max-width: 760px)').matches;", html)
            self.assertIn("chart-overview-type-calories", html)
            self.assertIn("chart-overview-type-duration", html)
            self.assertIn("chart-overview-type-intensity", html)
            self.assertIn("chart-sports-weekly-intensity-goal", html)
            self.assertIn("chart-sports-daily-calories-3d", html)
            self.assertIn("chart-sports-daily-duration-3d", html)
            self.assertIn("chart-health-weight-trend", html)
            self.assertIn("chart-health-body-age-trend", html)
            self.assertIn("chart-health-resting-hr-trend", html)
            self.assertIn("体重变化", html)
            self.assertIn("静息心率变化", html)
            self.assertNotIn("体重变化记录", html)
            self.assertNotIn("静息心率变化记录", html)
            self.assertIn("月度强度活动时间同比卡片", html)
            self.assertIn("compare-monthly-intensity-cards", html)
            self.assertIn("renderCompareMonthlyIntensityCards", html)
            self.assertIn("data-iso-toggle-group", html)
            self.assertIn('data-iso-mode="2d"', html)
            self.assertIn('data-iso-mode="3d"', html)
            self.assertIn('data-iso-mode="both"', html)
            self.assertIn("obelisk.js@1.2.1/build/obelisk.min.js", html)
            self.assertIn("buildIsoContributionData", html)
            self.assertIn("renderIsometricContributionChart", html)
            self.assertIn("renderFlatContributionGrid", html)
            self.assertIn("setIsoViewMode", html)
            self.assertIn("garmin-report-iso-view", html)
            self.assertIn("normalizeIsoAxisSize", html)
            self.assertIn("normalizeIsoCubeHeight", html)
            self.assertIn("tiltDegrees", html)
            self.assertIn("Math.PI / 180", html)
            self.assertIn("tiltDegrees: 60", html)
            self.assertIn("最佳一周", html)
            self.assertIn("最佳一天", html)
            self.assertIn("bestWeekTotal", html)
            self.assertNotIn("type: 'bar3D'", html)
            self.assertNotIn("grid3D", html)
            self.assertIn("activity-cards", html)
            self.assertIn("activity-card", html)
            self.assertIn("renderTopCards", html)
            self.assertIn("label.slice(0, 4) + '…'", html)
            self.assertIn(".report-shell.exporting .section-grid", html)
            self.assertIn("garmin-tab-change", html)
            self.assertIn("@media (max-width: 760px)", html)
            self.assertIn("grid-template-columns: 1fr", html)
            self.assertNotIn("同比变化百分比", html)
            self.assertNotIn("id=\"chart-compare-delta\"", html)
            self.assertIn("--bg-main: #05070f", html)
            self.assertIn('"previous_year": 2024', html)
            self.assertIn('"pct_change": -14.286', html)
            self.assertIn('"avg_daily_steps"', html)
            self.assertIn('"sleep_hours_by_month"', html)
            self.assertIn('"daily_trends"', html)
            self.assertIn('"display_names_zh"', html)
            self.assertIn('"by_intensity_minutes"', html)
            self.assertIn('"weekly_intensity_minutes"', html)
            self.assertIn('"monthly_intensity_compare_cards"', html)

    def test_comparison_rows_include_strength_and_badminton(self):
        analysis_data = {
            "activity_overview": {},
            "health_overview": {},
            "sports": {
                "running": {},
                "swimming": {},
                "strength_training": {
                    "change_vs_previous_year": {
                        "count": {"current": 20, "previous": 12, "delta": 8, "pct_change": 66.667},
                        "total_duration_s": {"current": 7200, "previous": 4500, "delta": 2700, "pct_change": 60.0},
                    }
                },
                "badminton": {
                    "change_vs_previous_year": {
                        "count": {"current": 35, "previous": 30, "delta": 5, "pct_change": 16.667},
                        "total_duration_s": {"current": 18000, "previous": 15000, "delta": 3000, "pct_change": 20.0},
                    }
                },
            },
            "monthly_trends": {},
            "daily_trends": {},
        }

        payload = report_module._build_report_payload_from_analysis(
            analysis_data=analysis_data,
            year=2025,
            previous_analysis_data={},
        )
        sections = {row.get("section") for row in payload.get("comparison_rows", []) if isinstance(row, dict)}
        self.assertIn("力量训练", sections)
        self.assertIn("羽毛球", sections)

    def test_monthly_intensity_compare_cards_include_12_months_and_yoy_delta(self):
        analysis_data = {
            "activity_overview": {},
            "health_overview": {},
            "sports": {},
            "monthly_trends": {},
            "daily_trends": {
                "intensity_minutes_by_date": {
                    "2025-01-01": 40,
                    "2025-01-10": 20,
                    "2025-02-02": 10,
                }
            },
        }
        previous_analysis_data = {
            "meta": {"year": 2024},
            "daily_trends": {
                "intensity_minutes_by_date": {
                    "2024-01-03": 20,
                    "2024-01-09": 10,
                    "2024-02-01": 10,
                }
            },
        }

        payload = report_module._build_report_payload_from_analysis(
            analysis_data=analysis_data,
            year=2025,
            previous_analysis_data=previous_analysis_data,
        )
        cards = payload.get("monthly_intensity_compare_cards", [])
        self.assertEqual(len(cards), 12)

        jan = cards[0]
        self.assertEqual(jan.get("month"), "01")
        self.assertEqual(jan.get("current_minutes"), 60.0)
        self.assertEqual(jan.get("previous_minutes"), 30.0)
        self.assertEqual(jan.get("delta_minutes"), 30.0)
        self.assertEqual(jan.get("pct_change"), 100.0)

        feb = cards[1]
        self.assertEqual(feb.get("month"), "02")
        self.assertEqual(feb.get("current_minutes"), 10.0)
        self.assertEqual(feb.get("previous_minutes"), 10.0)
        self.assertEqual(feb.get("delta_minutes"), 0.0)
        self.assertEqual(feb.get("pct_change"), 0.0)

    def test_load_previous_analysis_for_compare_rebuilds_when_daily_intensity_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            previous_dir = root / "garmin_report_2024"
            previous_analyze = previous_dir / "analyze" / "analyze_report_data.json"
            previous_analyze.parent.mkdir(parents=True, exist_ok=True)
            previous_analyze.write_text(
                json.dumps(
                    {
                        "meta": {"year": 2024},
                        "monthly_trends": {"distance_m_by_month": {"01": 1000}},
                    }
                ),
                encoding="utf-8",
            )
            rebuilt_payload = {
                "meta": {"year": 2024},
                "daily_trends": {"intensity_minutes_by_date": {"2024-01-01": 12}},
            }
            rebuilt_path = previous_dir / "analyze" / "rebuilt.json"

            with patch.object(report_module, "build_analysis_report", return_value=(rebuilt_payload, rebuilt_path)):
                payload, source_path = report_module.load_previous_analysis_for_compare(
                    previous_dir=previous_dir,
                    previous_year=2024,
                )

            self.assertEqual(payload, rebuilt_payload)
            self.assertEqual(source_path, rebuilt_path)


if __name__ == "__main__":
    unittest.main()
