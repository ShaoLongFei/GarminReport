<a id="english"></a>

# GarminReport

Language: **English** | [中文](#chinese)

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

---

<a id="chinese"></a>

# GarminReport（中文）

语言： [English](#english) | **中文**

GarminReport 是一个兼顾美观与隐私安全的 Garmin 年度报告项目。  
它可以把活动与健康数据整理成结构化年度页面，支持：

- 概览总览、运动分析、健康洞察、年度对比
- 多种图表与 3D/2D 热力可视化
- 一键打印 / 导出 PDF
- 桌面端与移动端自适应

## 快速开始

1. 复制环境变量模板：

```bash
cp .env.example .env
```

2. 安装依赖：

```bash
python -m pip install -r requirements.txt
```

3. 在 `.env` 中填写账号：

```env
GARMIN_EMAIL=
GARMIN_PASSWORD=
GARMIN_CN=false
```

4. 拉取数据（至少连续两年，才能做同比）：

```bash
python fetch_garmin_data.py --years 2024,2025
```

如果只拉取一年，分析时上一年对比字段会缺失。

5. 生成分析数据：

```bash
python analyze_report_data.py --year 2025
```

6. 生成报告：

```bash
python generate_report.py --year 2025
```

## 隐私说明

- 默认忽略 `garmin_report_*/` 原始数据目录。
- 默认忽略密钥与环境文件（如 `.env`、`*.pem` 等）。
- 默认忽略 `output/`，仅保留 `output/screenshots/*.png` 作为 README 示例图。
