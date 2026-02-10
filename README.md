# GarminReport

Generate a yearly Garmin activity and health report from locally pulled data.

## Privacy-first default

This repository is configured to keep personal data local only:

- `garmin_report_*/` is ignored
- `output/` screenshots and generated artifacts are ignored
- `.env` and other secret files are ignored

Do not commit raw Garmin exports, generated report JSON, or report HTML from personal data.

## Environment setup

1. Create a local `.env` file (never committed):

```bash
cp .env.example .env
```

2. Fill in your Garmin credentials in `.env`:

```env
GARMIN_EMAIL=
GARMIN_PASSWORD=
GARMIN_CN=false
```

## Typical local workflow

1. Pull data locally with `fetch_garmin_data.py`
2. Build yearly analysis with `analyze_report_data.py`
3. Generate report HTML with `generate_report.py`

All generated data and screenshots remain local by default.

## Optional privacy check before commit

Run staged-file privacy scan:

```bash
scripts/privacy_check_staged.sh
```

The script blocks commit if staged files contain common sensitive markers such as absolute local paths or user identifiers.
