# Garmin Report Redesign Design

## Summary
Build a dark, high-contrast, tech-styled annual Garmin report for 2025 with a 2024 comparison. Data is aggregated in Python from cached Garmin JSON and injected into a local HTML template. The frontend uses Tailwind CDN for layout, Alpine for tabs/accordion state, and ECharts + ECharts-GL for 2D/3D charts, including a custom 3D pie. Storyset SVGs are referenced as local assets. The report is fully static and self-contained once generated.

## Architecture
- Python reads cached Garmin JSON files for 2024 and 2025, normalizes activity data, computes KPIs and aggregates, and writes `report_data.json` plus `report_2025.html`.
- HTML template is a static skeleton with placeholders replaced by the Python generator.
- Frontend JS renders KPI grids, calendar comparison, tables, and charts from `window.REPORT_DATA`, and handles tab switching + pie mode switching.

## Components
- Hero: title, summary, generated timestamp, hero illustration.
- Tabs: Overview, Sports, Health, Compare.
- Overview: KPI grid and monthly calendar comparison blocks.
- Sports: 3D pie for activity types; running KPIs; top running table.
- Health: health trend charts; body charts (weight/metabolic age placeholders if absent).
- Compare: yearly comparison chart + monthly YoY trend chart.

## Data Flow
1. Python loads `activities_2024.json`, `activities_2025.json`, `health_data_2024.json`, `health_data_2025.json`.
2. Normalize activities to a DataFrame with dates, duration, distance, calories, HR fields.
3. Compute:
   - KPIs: count, distance_km, duration_h, calories, elev_m.
   - Monthly aggregates for comparison charts.
   - Activity-type distributions by count/duration/calories.
   - Running metrics: avgHR, maxHR, avgPace (mm:ss per km), plus top runs table.
4. Write `garmin_report_2025/data/report_data.json`.
5. Inject `REPORT_DATA`, `YEAR`, and `GENERATED_AT` into `report_template.html` to produce `report_2025.html`.
6. Frontend uses `window.REPORT_DATA` to render DOM + charts. Pie mode updates 3D series.

## Error Handling
- Python defaults missing fields to 0 or empty arrays; empty data yields safe placeholders.
- Frontend guards against empty datasets and missing nodes; renders empty state blocks without console errors.

## Testing / Verification
- Manual verification: generate report and open `garmin_report_2025/report_2025.html` to confirm tabs, charts (including 3D pie), KPIs, and tables render without console errors.
- No automated tests required per plan.
