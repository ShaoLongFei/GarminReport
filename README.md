# GarminReport

Language: **English** | [中文](README.zh-CN.md)

GarminReport turns your Garmin activity and health data into a polished annual report page.
It is built for personal use with a privacy-first workflow and publication-ready visuals.

## Live Demo

- [Demo](https://shaolongfei.github.io/GarminReport/index.html)

## Why GarminReport

- Narrative annual dashboard (Overview, Sports, Health, Year-over-Year)
- Rich chart set plus 3D/2D contribution-style visualizations
- One-click print and PDF export
- Responsive layout for desktop and mobile
- Local-first data flow for better privacy control

## Screenshot

Sports Analysis (Desktop):

[![Sports Analysis Desktop](output/screenshots/report-2025-sports-desktop.png)](https://shaolongfei.github.io/GarminReport/index.html)

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
