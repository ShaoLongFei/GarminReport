# GarminReport

Language: **English** | [中文](README.zh-CN.md)

GarminReport is a stylish, privacy-first annual dashboard for Garmin data.
It converts your activity and health records into a polished yearly report with:

- multi-section storytelling (Overview, Sports, Health, YoY)
- rich charts and 3D/2D contribution-style visualizations
- one-click print/PDF export
- responsive layout for desktop and mobile

## Screenshot

Sports Analysis (Desktop):

![Sports Analysis Desktop](output/screenshots/report-2025-sports-desktop.png)

## Quick Start

1. Configure env:

```bash
cp .env.example .env
```

2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Fill credentials in `.env`:

```env
GARMIN_EMAIL=
GARMIN_PASSWORD=
GARMIN_CN=false
```

4. Pull Garmin data (at least two consecutive years for YoY comparison):

```bash
python fetch_garmin_data.py --years 2024,2025
```

If only one year is pulled, previous-year comparison fields will be missing.

5. Build yearly analysis:

```bash
python analyze_report_data.py --year 2025
```

6. Generate report page:

```bash
python generate_report.py --year 2025
```

## Privacy & Safety

- `garmin_report_*/` is ignored by default.
- Secrets (`.env`, `*.pem`, `*.key`, `*.p12`) are ignored.
- `output/` is ignored except `output/screenshots/*.png` (for README demos).

## Project Structure

```text
requirements.txt            # Runtime dependencies
requirements-dev.txt        # Dev/test dependencies
fetch_garmin_data.py        # Pull raw Garmin data
analyze_report_data.py      # Build yearly aggregated analysis
generate_report.py          # Render final annual report HTML
templates/                  # HTML/CSS/JS templates and assets
tests/                      # Unit tests
output/screenshots/         # Demo screenshots tracked for README
```

## Testing

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```
