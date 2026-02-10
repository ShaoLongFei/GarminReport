#!/usr/bin/env python3
from __future__ import annotations

"""
Garmin数据分析报告生成脚本
功能：读取本地保存的Garmin数据，生成统计分析和HTML报告

使用方法:
    python generate_report.py --year 2025
    python generate_report.py --year 2025 --data-dir garmin_report_2025
"""

import json
import argparse
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - exercised in lightweight test env
    pd = None

try:
    import matplotlib.pyplot as plt
    import matplotlib
except ModuleNotFoundError:  # pragma: no cover
    plt = None
    matplotlib = None

try:
    import plotly.graph_objects as go
except ModuleNotFoundError:  # pragma: no cover
    go = None

# 设置中文字体支持
if matplotlib is not None:
    matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False

PROJECT_ROOT = Path(__file__).resolve().parent
REDESIGN_TEMPLATE_PATH = PROJECT_ROOT / "templates" / "redesign_report_template.html"
REDESIGN_CSS_PATH = PROJECT_ROOT / "templates" / "assets" / "report_redesign.css"
REDESIGN_JS_PATH = PROJECT_ROOT / "templates" / "assets" / "report_redesign.js"


def _require_dependency(name: str, module: Any):
    if module is None:
        raise RuntimeError(f"缺少依赖: {name}，请先安装后再运行报告生成。")


def _read_text_asset(path: Path, missing_msg: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"{missing_msg}: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_redesign_report_template() -> str:
    return _read_text_asset(REDESIGN_TEMPLATE_PATH, "报告模板不存在")


@lru_cache(maxsize=1)
def load_redesign_report_css() -> str:
    return _read_text_asset(REDESIGN_CSS_PATH, "报告样式不存在")


@lru_cache(maxsize=1)
def load_redesign_report_js() -> str:
    return _read_text_asset(REDESIGN_JS_PATH, "报告脚本不存在")


def normalize_activities(activities) -> pd.DataFrame:
    """
    兼容 garminconnect 不同方法/版本返回的结构：
    - list[dict]
    - dict 包含 activityList / activities / data 等
    并保证 startTimeLocal 列一定存在（没有就用 startTimeGMT 或 NaT）。
    """
    _require_dependency("pandas", pd)

    # 1) 先把 activities 规整成 list[dict]
    if activities is None:
        activities_list = []
    elif isinstance(activities, list):
        activities_list = activities
    elif isinstance(activities, dict):
        # 常见包裹字段名（不同接口/版本可能不同）
        for k in ("activityList", "activities", "data", "items"):
            v = activities.get(k)
            if isinstance(v, list):
                activities_list = v
                break
        else:
            # dict 但没找到 list：当成空
            activities_list = []
    else:
        activities_list = []

    # 2) 空数据直接返回一个带固定列的空 DF，避免 KeyError
    base_cols = [
        "activityId", "name", "type",
        "startTimeLocal", "startTimeGMT",
        "distance_m", "duration_s", "calories",
        "elevGain_m", "avgHR", "maxHR",
    ]
    if not activities_list:
        df = pd.DataFrame(columns=base_cols)
        df["startTimeLocal"] = pd.to_datetime(df["startTimeLocal"], errors="coerce")
        df["date"] = pd.NaT
        df["month"] = pd.NA
        df["distance_km"] = pd.to_numeric(df["distance_m"], errors="coerce") / 1000.0
        df["duration_h"] = pd.to_numeric(df["duration_s"], errors="coerce") / 3600.0
        return df

    # 3) 合并成 DataFrame
    df = pd.DataFrame(activities_list)

    # 4) 保证必需字段
    if "activityId" not in df.columns:
        df["activityId"] = range(len(df))
    if "activityName" in df.columns and "name" not in df.columns:
        df["name"] = df["activityName"]
    if "activityType" in df.columns and "type" not in df.columns:
        df["type"] = df["activityType"].apply(
            lambda x: x.get("typeKey", "unknown") if isinstance(x, dict) else x
        )
    if "distance" in df.columns and "distance_m" not in df.columns:
        df["distance_m"] = df["distance"]
    if "duration" in df.columns and "duration_s" not in df.columns:
        df["duration_s"] = df["duration"]
    if "elevationGain" in df.columns and "elevGain_m" not in df.columns:
        df["elevGain_m"] = df["elevationGain"]
    if "averageHR" in df.columns and "avgHR" not in df.columns:
        df["avgHR"] = df["averageHR"]

    # 5) 解决 startTimeLocal 缺失问题
    if "startTimeLocal" not in df.columns:
        # 先试试 startTimeGMT
        if "startTimeGMT" in df.columns:
            df["startTimeLocal"] = df["startTimeGMT"]
        else:
            # 彻底没有 => 给 NaT
            df["startTimeLocal"] = pd.NaT

    # 6) 转成 datetime，并衍生 date/month
    df["startTimeLocal"] = pd.to_datetime(df["startTimeLocal"], errors="coerce")
    df["date"] = df["startTimeLocal"].dt.date
    df["month"] = df["startTimeLocal"].dt.month

    # 7) 数值型转换
    df["distance_km"] = pd.to_numeric(df.get("distance_m", 0), errors="coerce") / 1000.0
    df["duration_h"] = pd.to_numeric(df.get("duration_s", 0), errors="coerce") / 3600.0

    return df


def analyze_health_data(health_data: dict, year: int) -> dict:
    """
    分析健康数据，返回统计信息
    
    Args:
        health_data: 健康数据字典
        year: 年份
        
    Returns:
        dict: 健康数据统计
    """
    stats = {
        'total_days': 0,
        'sleep': {},
        'steps': {},
        'hrv': {}
    }
    
    # 睡眠统计（兼容多种结构）
    sleep_records = health_data.get('sleep', [])
    if sleep_records:
      sleep_durations = []
      deep_sleep_durations = []
      sleep_scores = []

      for record in sleep_records:
        data = None
        if isinstance(record, dict):
          if isinstance(record.get('data'), dict):
            data = record.get('data')
          elif isinstance(record.get('dailySleepDTO'), dict):
            data = record.get('dailySleepDTO')
          elif isinstance(record.get('sleepData'), dict):
            data = record.get('sleepData')
          else:
            data = record

        if isinstance(data, dict):
          duration_sec = data.get('sleepTimeSeconds') or data.get('totalSleepSeconds') or 0
          deep_sec = data.get('deepSleepSeconds') or 0
          score = None
          scores_obj = data.get('sleepScores')
          if isinstance(scores_obj, dict):
            overall = scores_obj.get('overall')
            if isinstance(overall, dict):
              score = overall.get('value')
          if score is None:
            score = data.get('overallSleepScore')

          if duration_sec:
            sleep_durations.append(duration_sec / 3600.0)
          if deep_sec:
            deep_sleep_durations.append(deep_sec / 3600.0)
          if isinstance(score, (int, float)):
            sleep_scores.append(float(score))

      stats['sleep'] = {
        'count': len(sleep_records),
        'avg_duration': sum(sleep_durations) / len(sleep_durations) if sleep_durations else 0,
        'total_duration': sum(sleep_durations),
        'avg_deep_sleep': sum(deep_sleep_durations) / len(deep_sleep_durations) if deep_sleep_durations else 0,
        'avg_sleep_score': sum(sleep_scores) / len(sleep_scores) if sleep_scores else 0,
      }
    
    # 步数统计（兼容多种结构）
    steps_records = health_data.get('steps', [])
    steps_values = []
    if steps_records:
      for r in steps_records:
        if isinstance(r, dict):
          if 'steps' in r:
            steps_values.append(r.get('steps', 0))
          elif 'totalSteps' in r:
            steps_values.append(r.get('totalSteps', 0))
          elif isinstance(r.get('data'), dict):
            steps_values.append(r['data'].get('totalSteps', 0))

    # 若 steps 为空，尝试从 daily_summary 中提取
    if not steps_values:
      for d in health_data.get('daily_summary', []):
        if isinstance(d, dict):
          if 'totalSteps' in d:
            steps_values.append(d.get('totalSteps', 0))
          elif isinstance(d.get('data'), dict):
            steps_values.append(d['data'].get('totalSteps', 0))

    if steps_values:
      total_steps = sum(steps_values)
      avg_steps = total_steps / len(steps_values) if steps_values else 0
      stats['steps'] = {
        'count': len(steps_values),
        'total': total_steps,
        'avg_daily': avg_steps,
      }
    
    # HRV统计
    hrv_records = health_data.get('hrv', [])
    stats['hrv'] = {
      'count': len(hrv_records),
    }
    
    # 每日汇总统计
    daily_summary = health_data.get('daily_summary', [])
    stats['total_days'] = len(daily_summary)
    if daily_summary:
      intensity_values = []
      for d in daily_summary:
        if not isinstance(d, dict):
          continue
        row = d.get('data') if isinstance(d.get('data'), dict) else d
        moderate = row.get('moderateIntensityMinutes', 0) if isinstance(row, dict) else 0
        vigorous = row.get('vigorousIntensityMinutes', 0) if isinstance(row, dict) else 0
        moderate_val = float(moderate) if isinstance(moderate, (int, float)) else 0.0
        vigorous_val = float(vigorous) if isinstance(vigorous, (int, float)) else 0.0
        intensity_values.append(moderate_val + 2.0 * vigorous_val)
      stats['intensity'] = {
        'avg_daily': sum(intensity_values) / len(intensity_values) if intensity_values else 0,
      }
    else:
      stats['intensity'] = {'avg_daily': 0}
    
    return stats


def _plotly_embed_html(data: Any, layout: dict, height: int = 360) -> str:
  chart_id = f"plot_{uuid4().hex}"
  data_json = json.dumps(data, ensure_ascii=False)
  layout_json = json.dumps(layout, ensure_ascii=False)
  config_json = json.dumps({"responsive": True, "displayModeBar": False}, ensure_ascii=False)
  return f"""
<div id="{chart_id}" style="height:{height}px;"></div>
<script>
(() => {{
  const el = document.getElementById("{chart_id}");
  if (!el || !window.Plotly) {{
    if (el) el.innerHTML = '<div class="muted">Plotly.js 未加载，图表不可用</div>';
    return;
  }}
  Plotly.newPlot("{chart_id}", {data_json}, {layout_json}, {config_json});
}})();
</script>
"""


def build_isometric_heatmap_3d(daily_map: dict, year: int, title: str, colorscale: str, unit: str) -> str:
  """生成 GitHub 风格等距 3D 热力图（方块阵列）"""
  dates: list[date] = []
  current = date(year, 1, 1)
  end = date(year, 12, 31)
  while current <= end:
    dates.append(current)
    current += timedelta(days=1)

  values = [float(daily_map.get(d, 0) or 0) for d in dates]
  max_val = max(values) if values else 0

  if max_val == 0:
    if go is not None:
      fig = go.Figure()
      fig.add_annotation(text="暂无数据", x=0.5, y=0.5, showarrow=False)
      fig.update_layout(height=420, margin=dict(l=40, r=20, t=50, b=40))
      return fig.to_html(include_plotlyjs=False, full_html=False)
    return '<div class="muted">暂无数据</div>'

  cube_size = 0.7
  cube_gap = 0.3
  base_height = 0.03
  height_scale = 1.6

  xs, ys, zs, intensity = [], [], [], []
  I, J, K = [], [], []
  hover_x, hover_y, hover_z, hover_text = [], [], [], []

  for d, val in zip(dates, values):
    week_idx = int(((d - date(year, 1, 1)).days) // 7)
    weekday = int(d.weekday())
    height = (val / max_val) * height_scale + base_height

    x0 = week_idx * (cube_size + cube_gap)
    y0 = weekday * (cube_size + cube_gap)
    z0 = 0
    x1, y1, z1 = x0 + cube_size, y0 + cube_size, height

    # 8 vertices of cube
    v = [
      (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
      (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)
    ]
    idx = len(xs)
    for vx, vy, vz in v:
      xs.append(vx); ys.append(vy); zs.append(vz)
      intensity.append(val)

    # 12 triangles (two per face)
    faces = [
      (0, 1, 2), (0, 2, 3),  # bottom
      (4, 5, 6), (4, 6, 7),  # top
      (0, 1, 5), (0, 5, 4),  # front
      (1, 2, 6), (1, 6, 5),  # right
      (2, 3, 7), (2, 7, 6),  # back
      (3, 0, 4), (3, 4, 7),  # left
    ]
    for a, b, c in faces:
      I.append(idx + a); J.append(idx + b); K.append(idx + c)

    hover_x.append(x0 + cube_size / 2)
    hover_y.append(y0 + cube_size / 2)
    hover_z.append(z1)
    hover_text.append(f"{d.isoformat()}<br>{val:.2f} {unit}")

  if go is None:
    # 依赖缺失时改用前端 Plotly.js 绘制 3D 散点热力图，保持每天一个点。
    data = [
      {
        "type": "scatter3d",
        "mode": "markers",
        "x": hover_x,
        "y": hover_y,
        "z": hover_z,
        "text": hover_text,
        "hoverinfo": "text",
        "marker": {
          "size": 4,
          "opacity": 0.9,
          "color": values,
          "colorscale": colorscale,
          "showscale": True,
        },
      }
    ]
    layout = {
      "title": title,
      "height": 520,
      "margin": {"l": 40, "r": 20, "t": 50, "b": 40},
      "scene": {
        "xaxis": {"visible": False},
        "yaxis": {"visible": False},
        "zaxis": {"visible": False},
        "aspectratio": {"x": 3.2, "y": 1.2, "z": 0.7},
        "camera": {"eye": {"x": 2.6, "y": 2.2, "z": 1.2}},
      },
    }
    return _plotly_embed_html(data=data, layout=layout, height=520)

  mesh = go.Mesh3d(
    x=xs, y=ys, z=zs,
    i=I, j=J, k=K,
    intensity=intensity,
    colorscale=colorscale,
    flatshading=True,
    showscale=True,
    lighting=dict(ambient=0.6, diffuse=0.8, roughness=0.6, specular=0.2)
  )

  hover = go.Scatter3d(
    x=hover_x, y=hover_y, z=hover_z,
    mode="markers",
    marker=dict(size=2, opacity=0),
    text=hover_text,
    hoverinfo="text"
  )

  fig = go.Figure(data=[mesh, hover])
  fig.update_layout(
    title=title,
    height=520,
    margin=dict(l=40, r=20, t=50, b=40),
    scene=dict(
      xaxis=dict(visible=False),
      yaxis=dict(visible=False),
      zaxis=dict(visible=False),
      aspectratio=dict(x=3.2, y=1.2, z=0.7),
      camera=dict(eye=dict(x=2.6, y=2.2, z=1.2))
    )
  )
  return fig.to_html(include_plotlyjs=False, full_html=False)


def build_plotly_charts(df: pd.DataFrame, year: int) -> dict:
    """生成 Plotly 图表 HTML 片段"""
    _require_dependency("pandas", pd)
    _require_dependency("plotly", go)
    if df.empty:
        return {
            'monthly_distance': '<div class="muted">暂无数据</div>',
            'type_duration': '<div class="muted">暂无数据</div>',
            'monthly_count': '<div class="muted">暂无数据</div>',
            'duration_heatmap_3d': '<div class="muted">暂无数据</div>',
            'calories_heatmap_3d': '<div class="muted">暂无数据</div>',
        }

    # 月度距离
    by_month = (
        df.groupby("month", dropna=True)["distance_km"]
        .sum()
        .sort_index()
    )
    fig1 = go.Figure([
      go.Bar(x=by_month.index.astype(str), y=by_month.values, marker_color="#4C78A8")
    ])
    fig1.update_layout(title=f"月度总距离 (km) - {year}", height=360, margin=dict(l=40, r=20, t=50, b=40))

    # 运动类型时长
    by_type = (
      df.groupby("type", dropna=True)["duration_h"]
      .sum()
      .sort_values(ascending=False)
      .head(12)
    )
    fig2 = go.Figure([
      go.Bar(x=by_type.index.astype(str), y=by_type.values, marker_color="#F58518")
    ])
    fig2.update_layout(title=f"运动类型时长 (小时) - {year}", height=360, margin=dict(l=40, r=20, t=50, b=90))

    # 月度次数
    by_month_count = df.groupby("month", dropna=True).size().sort_index()
    fig3 = go.Figure([
      go.Scatter(x=by_month_count.index.astype(str), y=by_month_count.values, mode="lines+markers", line=dict(color="#54A24B"))
    ])
    fig3.update_layout(title=f"月度活动次数 - {year}", height=360, margin=dict(l=40, r=20, t=50, b=40))

    # 按日期汇总时长与卡路里
    if "date" in df.columns:
      daily = df.groupby("date").agg(
        duration_h=("duration_h", "sum"),
        calories=("calories", "sum"),
      ).reset_index()
    else:
      daily = pd.DataFrame(columns=["date", "duration_h", "calories"])

    daily_map_duration = {}
    daily_map_calories = {}
    if not daily.empty:
      for _, row in daily.iterrows():
        d = row.get("date")
        if pd.isna(d):
          continue
        if not isinstance(d, (pd.Timestamp,)):
          d = pd.to_datetime(d, errors="coerce")
        if pd.isna(d):
          continue
        daily_map_duration[d.date()] = float(row.get("duration_h") or 0)
        daily_map_calories[d.date()] = float(row.get("calories") or 0)

    duration_heatmap_3d = build_isometric_heatmap_3d(
      daily_map_duration, year, f"活动时长 3D 热力图 - {year}", "Blues", "h"
    )
    calories_heatmap_3d = build_isometric_heatmap_3d(
      daily_map_calories, year, f"卡路里消耗 3D 热力图 - {year}", "Reds", "kcal"
    )

    return {
      'monthly_distance': fig1.to_html(include_plotlyjs=False, full_html=False),
      'type_duration': fig2.to_html(include_plotlyjs=False, full_html=False),
      'monthly_count': fig3.to_html(include_plotlyjs=False, full_html=False),
      'duration_heatmap_3d': duration_heatmap_3d,
      'calories_heatmap_3d': calories_heatmap_3d,
    }


def make_plots(df: pd.DataFrame, out_dir: Path, year: int) -> dict:
    """
    生成统计图表
    
    Args:
        df: 活动数据DataFrame
        out_dir: 输出目录
        year: 年份
        
    Returns:
        dict: 图表文件名字典
    """
    _require_dependency("matplotlib", plt)
    _require_dependency("pandas", pd)
    out_dir.mkdir(parents=True, exist_ok=True)
    plots = {}

    # 月度距离
    by_month = (
        df.groupby("month", dropna=True)[["distance_km", "duration_h"]]
        .sum()
        .sort_index()
    )

    p1 = out_dir / f"monthly_distance_{year}.png"
    plt.figure(figsize=(10, 6))
    by_month["distance_km"].plot(kind="bar", color='steelblue')
    plt.title(f"月度总距离 (km) - {year}", fontsize=14, pad=20)
    plt.xlabel("月份", fontsize=12)
    plt.ylabel("公里 (km)", fontsize=12)
    plt.xticks(rotation=0)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(p1, dpi=150, bbox_inches='tight')
    plt.close()
    plots['monthly_distance'] = p1.name

    # 运动类型占比（按时长）
    by_type = (
        df.groupby("type", dropna=True)["duration_h"]
        .sum()
        .sort_values(ascending=False)
        .head(12)
    )
    p2 = out_dir / f"type_duration_{year}.png"
    plt.figure(figsize=(10, 6))
    by_type.plot(kind="bar", color='coral')
    plt.title(f"运动类型时长统计 (小时) - {year}", fontsize=14, pad=20)
    plt.xlabel("运动类型", fontsize=12)
    plt.ylabel("小时 (h)", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(p2, dpi=150, bbox_inches='tight')
    plt.close()
    plots['type_duration'] = p2.name

    # 月度活动次数
    by_month_count = df.groupby("month", dropna=True).size()
    p3 = out_dir / f"monthly_count_{year}.png"
    plt.figure(figsize=(10, 6))
    by_month_count.plot(kind="bar", color='mediumseagreen')
    plt.title(f"月度活动次数 - {year}", fontsize=14, pad=20)
    plt.xlabel("月份", fontsize=12)
    plt.ylabel("活动次数", fontsize=12)
    plt.xticks(rotation=0)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(p3, dpi=150, bbox_inches='tight')
    plt.close()
    plots['monthly_count'] = p3.name

    return plots


def analysis_report_candidates(data_dir: Path) -> list[Path]:
    return [
        data_dir / "analyze" / "analyze_report_data.json",
        data_dir / "analyze_report_data.json",
    ]


def load_analysis_report(data_dir: Path) -> tuple[dict[str, Any], Path]:
    for candidate in analysis_report_candidates(data_dir):
        if not candidate.exists():
            continue
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload, candidate
    raise FileNotFoundError(f"未找到分析数据文件: {analysis_report_candidates(data_dir)}")


def build_analysis_report(year: int, data_dir: Path) -> tuple[dict[str, Any], Path]:
    from analyze_report_data import analyze_report_for_year, write_analyze_report

    report_root = data_dir.parent
    payload = analyze_report_for_year(year=year, report_root=report_root, strict=False)
    output = write_analyze_report(year=year, report_root=report_root, data=payload, pretty=True)
    return payload, output


def build_plotly_charts_from_analysis(analysis_data: dict, year: int) -> dict:
    monthly = analysis_data.get("monthly_trends", {}) if isinstance(analysis_data, dict) else {}
    sports = analysis_data.get("sports", {}) if isinstance(analysis_data, dict) else {}
    daily = analysis_data.get("daily_trends", {}) if isinstance(analysis_data, dict) else {}

    distance_m_by_month = monthly.get("distance_m_by_month", {})
    activity_count_by_month = monthly.get("activity_count_by_month", {})
    month_labels = [f"{i:02d}" for i in range(1, 13)]
    monthly_distance_km = [float(distance_m_by_month.get(m, 0) or 0) / 1000.0 for m in month_labels]
    monthly_count = [float(activity_count_by_month.get(m, 0) or 0) for m in month_labels]

    if go is not None:
        fig1 = go.Figure([go.Bar(x=month_labels, y=monthly_distance_km, marker_color="#4C78A8")])
        fig1.update_layout(title=f"月度总距离 (km) - {year}", height=360, margin=dict(l=40, r=20, t=50, b=40))
        monthly_distance_html = fig1.to_html(include_plotlyjs=False, full_html=False)
    else:
        monthly_distance_html = _plotly_embed_html(
            data=[{"type": "bar", "x": month_labels, "y": monthly_distance_km, "marker": {"color": "#4C78A8"}}],
            layout={"title": f"月度总距离 (km) - {year}", "height": 360, "margin": {"l": 40, "r": 20, "t": 50, "b": 40}},
            height=360,
        )

    type_labels = []
    type_hours = []
    if isinstance(sports, dict):
        for key, val in sports.items():
            if not isinstance(val, dict):
                continue
            if key.startswith("sport_type_"):
                continue
            if "total_duration_s" not in val:
                continue
            type_labels.append(key)
            type_hours.append(float(val.get("total_duration_s", 0) or 0) / 3600.0)
    if go is not None:
        fig2 = go.Figure([go.Bar(x=type_labels, y=type_hours, marker_color="#F58518")])
        fig2.update_layout(title=f"运动类型时长 (小时) - {year}", height=360, margin=dict(l=40, r=20, t=50, b=90))
        type_duration_html = fig2.to_html(include_plotlyjs=False, full_html=False)
    else:
        type_duration_html = _plotly_embed_html(
            data=[{"type": "bar", "x": type_labels, "y": type_hours, "marker": {"color": "#F58518"}}],
            layout={"title": f"运动类型时长 (小时) - {year}", "height": 360, "margin": {"l": 40, "r": 20, "t": 50, "b": 90}},
            height=360,
        )

    if go is not None:
        fig3 = go.Figure([go.Scatter(x=month_labels, y=monthly_count, mode="lines+markers", line=dict(color="#54A24B"))])
        fig3.update_layout(title=f"月度活动次数 - {year}", height=360, margin=dict(l=40, r=20, t=50, b=40))
        monthly_count_html = fig3.to_html(include_plotlyjs=False, full_html=False)
    else:
        monthly_count_html = _plotly_embed_html(
            data=[{"type": "scatter", "mode": "lines+markers", "x": month_labels, "y": monthly_count, "line": {"color": "#54A24B"}}],
            layout={"title": f"月度活动次数 - {year}", "height": 360, "margin": {"l": 40, "r": 20, "t": 50, "b": 40}},
            height=360,
        )

    duration_h_by_date = daily.get("duration_h_by_date", {}) if isinstance(daily, dict) else {}
    calories_by_date = daily.get("calories_by_date", {}) if isinstance(daily, dict) else {}
    duration_map = {}
    calories_map = {}
    for k, v in duration_h_by_date.items():
        try:
            duration_map[date.fromisoformat(str(k)[:10])] = float(v or 0)
        except Exception:
            continue
    for k, v in calories_by_date.items():
        try:
            calories_map[date.fromisoformat(str(k)[:10])] = float(v or 0)
        except Exception:
            continue

    duration_heatmap_3d = build_isometric_heatmap_3d(duration_map, year, f"活动时长 3D 热力图 - {year}", "Blues", "h")
    calories_heatmap_3d = build_isometric_heatmap_3d(calories_map, year, f"卡路里消耗 3D 热力图 - {year}", "Reds", "kcal")

    return {
        'monthly_distance': monthly_distance_html,
        'type_duration': type_duration_html,
        'monthly_count': monthly_count_html,
        'duration_heatmap_3d': duration_heatmap_3d,
        'calories_heatmap_3d': calories_heatmap_3d,
    }


def _format_pace_min_per_km(value: Any) -> str:
    v = float(value) if isinstance(value, (int, float)) else None
    if v is None or v <= 0:
        return "N/A"
    return f"{v:.2f} min/km"


def _format_pace_min_per_100m(value: Any, distance_m: Any = None, duration_s: Any = None) -> str:
    if isinstance(value, (int, float)) and value > 0:
        return f"{float(value):.2f} min/100m"
    d = float(distance_m) if isinstance(distance_m, (int, float)) else 0.0
    t = float(duration_s) if isinstance(duration_s, (int, float)) else 0.0
    if d <= 0 or t <= 0:
        return "N/A"
    pace = (t / 60.0) / (d / 100.0)
    return f"{pace:.2f} min/100m"


def _render_top_activity_table(records: list[dict[str, Any]], include_type: bool = False) -> str:
    if not records:
        return '<div class="muted">暂无数据</div>'

    head = "<th>日期</th>"
    if include_type:
        head += "<th>类型</th>"
    head += "<th>名称</th><th>距离</th><th>时长</th>"

    rows = []
    for r in records:
        date_text = str(r.get("date") or "")
        type_text = str(r.get("type_key") or "")
        name_text = str(r.get("activity_name") or "")
        distance_m = float(r.get("distance_m") or 0.0)
        duration_s = float(r.get("duration_s") or 0.0)
        row = f"<td>{date_text}</td>"
        if include_type:
            row += f"<td>{type_text}</td>"
        row += (
            f"<td>{name_text}</td>"
            f"<td>{distance_m / 1000.0:.2f} km</td>"
            f"<td>{duration_s / 3600.0:.2f} h</td>"
        )
        rows.append(f"<tr>{row}</tr>")

    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _pie_html(values: list[float], labels: list[str], title: str) -> str:
    if go is None:
        if not values:
            return '<div class="muted">暂无数据</div>'
        return _plotly_embed_html(
            data=[
                {
                    "type": "pie",
                    "labels": labels,
                    "values": values,
                    "hole": 0.35,
                    "textinfo": "percent+label",
                    "textposition": "outside",
                }
            ],
            layout={"title": title, "height": 360, "margin": {"l": 40, "r": 20, "t": 50, "b": 40}},
            height=360,
        )
    if not values:
        fig = go.Figure()
        fig.add_annotation(text="暂无数据", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=360, margin=dict(l=40, r=20, t=50, b=40))
        return fig.to_html(include_plotlyjs=False, full_html=False)
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.35,
                pull=[0.02] * len(values),
                textinfo="percent+label",
                textposition="outside",
            )
        ]
    )
    fig.update_layout(title=title, height=360, margin=dict(l=40, r=20, t=50, b=40))
    return fig.to_html(include_plotlyjs=False, full_html=False)


def _numeric_distribution_items(payload: dict[str, Any]) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    for k, v in payload.items():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            rows.append((str(k), float(v)))
    return rows


SPORT_TYPE_ZH_MAP: dict[str, str] = {
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


def _localized_sport_type_labels(
    dist_map: dict[str, Any],
    display_names_zh: dict[str, Any] | None = None,
) -> tuple[list[str], list[float]]:
    display_map = display_names_zh if isinstance(display_names_zh, dict) else {}
    labels: list[str] = []
    values: list[float] = []
    for key, value in _numeric_distribution_items(dist_map if isinstance(dist_map, dict) else {}):
        zh = display_map.get(key)
        if not isinstance(zh, str) or not zh.strip():
            zh = SPORT_TYPE_ZH_MAP.get(key, key)
        labels.append(zh)
        values.append(float(value))
    return labels, values


def _build_type_analysis_section_html(sports: dict[str, Any]) -> str:
    sport_type_analysis = sports.get("sport_type_analysis", {}) if isinstance(sports, dict) else {}

    by_count = sport_type_analysis.get("by_count") if isinstance(sport_type_analysis, dict) else None
    by_duration = sport_type_analysis.get("by_duration_s") if isinstance(sport_type_analysis, dict) else None
    by_calories = sport_type_analysis.get("by_calories") if isinstance(sport_type_analysis, dict) else None
    by_distance = sport_type_analysis.get("by_distance_m") if isinstance(sport_type_analysis, dict) else None
    display_names = sport_type_analysis.get("display_names_zh") if isinstance(sport_type_analysis, dict) else None

    if not isinstance(by_count, dict):
        by_count = sports.get("sport_type_distribution", {}) if isinstance(sports, dict) else {}
    if not isinstance(by_duration, dict):
        by_duration = sports.get("sport_type_duration_s_distribution", {}) if isinstance(sports, dict) else {}
    if not isinstance(by_calories, dict):
        by_calories = sports.get("sport_type_calories_distribution", {}) if isinstance(sports, dict) else {}
    if not isinstance(by_distance, dict):
        by_distance = sports.get("sport_type_distance_m_distribution", {}) if isinstance(sports, dict) else {}

    count_labels, count_values = _localized_sport_type_labels(by_count, display_names)
    duration_labels, duration_values = _localized_sport_type_labels(by_duration, display_names)
    calories_labels, calories_values = _localized_sport_type_labels(by_calories, display_names)
    distance_labels, distance_values = _localized_sport_type_labels(by_distance, display_names)

    duration_values_h = [v / 3600.0 for v in duration_values]
    distance_values_km = [v / 1000.0 for v in distance_values]

    return f"""
    <div class=\"card\">
      <h2>运动类型分析</h2>
      <div class=\"type-analysis-grid\">
        <div class=\"type-analysis-item\">{_pie_html(count_values, count_labels, "各运动类型次数占比")}</div>
        <div class=\"type-analysis-item\">{_pie_html(duration_values_h, duration_labels, "各运动类型总时长占比")}</div>
        <div class=\"type-analysis-item\">{_pie_html(calories_values, calories_labels, "各运动类型总卡路里占比")}</div>
        <div class=\"type-analysis-item\">{_pie_html(distance_values_km, distance_labels, "各运动类型总距离占比")}</div>
      </div>
    </div>
"""


def _as_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _month_series(source: dict[str, Any] | None) -> tuple[list[str], list[float]]:
    labels = [f"{i:02d}" for i in range(1, 13)]
    payload = source if isinstance(source, dict) else {}
    return labels, [_as_float(payload.get(m, 0.0), 0.0) for m in labels]


def _normalize_daily_map(source: Any) -> dict[str, float]:
    payload = source if isinstance(source, dict) else {}
    normalized: dict[str, float] = {}
    for key, value in payload.items():
        date_key = str(key)[:10]
        if not date_key:
            continue
        normalized[date_key] = round(_as_float(value, 0.0), 3)
    return normalized


def _build_weekly_intensity_minutes_series(
    year: int,
    intensity_minutes_by_date: dict[str, float],
    goal_minutes: float = 200.0,
) -> dict[str, Any]:
    first_day = date(year, 1, 1)
    last_day = date(year, 12, 31)
    first_week_start = first_day - timedelta(days=first_day.weekday())
    total_weeks = ((last_day - first_week_start).days // 7) + 1
    weekly_totals = [0.0] * total_weeks

    for day_text, value in intensity_minutes_by_date.items():
        try:
            day = date.fromisoformat(str(day_text)[:10])
        except Exception:
            continue
        if day.year != year:
            continue
        week_index = (day - first_week_start).days // 7
        if 0 <= week_index < total_weeks:
            weekly_totals[week_index] += max(0.0, _as_float(value, 0.0))

    return {
        "labels": [f"W{i + 1:02d}" for i in range(total_weeks)],
        "actual_minutes": [round(v, 3) for v in weekly_totals],
        "goal_minutes": round(max(0.0, goal_minutes), 3),
    }


def _top_activity_rows(records: Any, include_type: bool = False) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        row = {
            "date": str(item.get("date") or ""),
            "activity_name": str(item.get("activity_name") or ""),
            "distance_km": round(_as_float(item.get("distance_m")) / 1000.0, 2),
            "duration_h": round(_as_float(item.get("duration_s")) / 3600.0, 2),
        }
        if include_type:
            row["type_key"] = str(item.get("type_key") or "")
        rows.append(row)
    return rows


def _change_rows(
    changes: Any,
    key_to_label: dict[str, str],
    key_to_unit: dict[str, str],
    section: str,
) -> list[dict[str, Any]]:
    if not isinstance(changes, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key, label in key_to_label.items():
        payload = changes.get(key)
        if not isinstance(payload, dict):
            continue
        rows.append(
            {
                "section": section,
                "key": key,
                "label": label,
                "unit": key_to_unit.get(key, ""),
                "current": _as_float(payload.get("current"), 0.0),
                "previous": _as_float(payload.get("previous"), 0.0),
                "delta": _as_float(payload.get("delta"), 0.0),
                "pct_change": _as_float(payload.get("pct_change"), 0.0),
            }
        )
    return rows


def _build_report_payload_from_analysis(
    analysis_data: dict[str, Any],
    year: int,
    previous_analysis_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    activity_overview = analysis_data.get("activity_overview", {}) if isinstance(analysis_data, dict) else {}
    health_overview = analysis_data.get("health_overview", {}) if isinstance(analysis_data, dict) else {}
    health_advanced = analysis_data.get("health_advanced", {}) if isinstance(analysis_data, dict) else {}
    sports = analysis_data.get("sports", {}) if isinstance(analysis_data, dict) else {}
    monthly = analysis_data.get("monthly_trends", {}) if isinstance(analysis_data, dict) else {}

    run_stats = sports.get("running", {}) if isinstance(sports, dict) else {}
    swim_stats = sports.get("swimming", {}) if isinstance(sports, dict) else {}
    strength_stats = sports.get("strength_training", {}) if isinstance(sports, dict) else {}
    badminton_stats = sports.get("badminton", {}) if isinstance(sports, dict) else {}

    sport_type_analysis = sports.get("sport_type_analysis", {}) if isinstance(sports, dict) else {}
    by_count = sport_type_analysis.get("by_count") if isinstance(sport_type_analysis, dict) else None
    by_duration = sport_type_analysis.get("by_duration_s") if isinstance(sport_type_analysis, dict) else None
    by_calories = sport_type_analysis.get("by_calories") if isinstance(sport_type_analysis, dict) else None
    by_distance = sport_type_analysis.get("by_distance_m") if isinstance(sport_type_analysis, dict) else None
    by_intensity = sport_type_analysis.get("by_intensity_minutes") if isinstance(sport_type_analysis, dict) else None
    display_names = sport_type_analysis.get("display_names_zh") if isinstance(sport_type_analysis, dict) else None

    if not isinstance(by_count, dict):
        by_count = sports.get("sport_type_distribution", {}) if isinstance(sports, dict) else {}
    if not isinstance(by_duration, dict):
        by_duration = sports.get("sport_type_duration_s_distribution", {}) if isinstance(sports, dict) else {}
    if not isinstance(by_calories, dict):
        by_calories = sports.get("sport_type_calories_distribution", {}) if isinstance(sports, dict) else {}
    if not isinstance(by_distance, dict):
        by_distance = sports.get("sport_type_distance_m_distribution", {}) if isinstance(sports, dict) else {}

    sport_keys: list[str] = []
    for payload in (by_count, by_duration, by_calories, by_distance):
        if not isinstance(payload, dict):
            continue
        for key, value in payload.items():
            if not isinstance(key, str):
                continue
            if isinstance(value, bool):
                continue
            if not isinstance(value, (int, float)):
                continue
            if key not in sport_keys:
                sport_keys.append(key)

    display_map = display_names if isinstance(display_names, dict) else {}
    sport_labels = []
    sport_count = []
    sport_duration_h = []
    sport_calories = []
    sport_distance_km = []
    sport_intensity_minutes = []
    total_intensity_minutes = _as_float(health_overview.get("total_intensity_minutes"), 0.0)
    calories_total = 0.0
    duration_total_h = 0.0
    for key in sport_keys:
        display = display_map.get(key)
        if not isinstance(display, str) or not display.strip():
            display = SPORT_TYPE_ZH_MAP.get(key, key)
        sport_labels.append(display)
        count_value = _as_float(by_count.get(key), 0.0)
        duration_h_value = _as_float(by_duration.get(key), 0.0) / 3600.0
        calories_value = _as_float(by_calories.get(key), 0.0)
        distance_km_value = _as_float(by_distance.get(key), 0.0) / 1000.0
        sport_count.append(count_value)
        sport_duration_h.append(duration_h_value)
        sport_calories.append(calories_value)
        sport_distance_km.append(distance_km_value)
        calories_total += max(0.0, calories_value)
        duration_total_h += max(0.0, duration_h_value)
        if isinstance(by_intensity, dict):
            sport_intensity_minutes.append(_as_float(by_intensity.get(key), 0.0))
        else:
            sport_intensity_minutes.append(0.0)

    if not isinstance(by_intensity, dict):
        estimated: list[float] = []
        for idx in range(len(sport_labels)):
            if total_intensity_minutes > 0.0 and calories_total > 0.0:
                ratio = max(0.0, sport_calories[idx]) / calories_total
                estimated.append(total_intensity_minutes * ratio)
            elif total_intensity_minutes > 0.0 and duration_total_h > 0.0:
                ratio = max(0.0, sport_duration_h[idx]) / duration_total_h
                estimated.append(total_intensity_minutes * ratio)
            else:
                estimated.append(max(0.0, sport_duration_h[idx]) * 60.0)
        sport_intensity_minutes = [round(v, 3) for v in estimated]
    else:
        sport_intensity_minutes = [round(max(0.0, v), 3) for v in sport_intensity_minutes]

    month_labels, distance_m = _month_series(monthly.get("distance_m_by_month") if isinstance(monthly, dict) else {})
    _, activity_count = _month_series(monthly.get("activity_count_by_month") if isinstance(monthly, dict) else {})
    _, steps_by_month = _month_series(monthly.get("steps_by_month") if isinstance(monthly, dict) else {})
    _, sleep_hours_by_month = _month_series(monthly.get("sleep_hours_by_month") if isinstance(monthly, dict) else {})
    distance_km = [round(v / 1000.0, 3) for v in distance_m]
    daily_trends = analysis_data.get("daily_trends", {}) if isinstance(analysis_data, dict) else {}
    raw_daily_duration = daily_trends.get("duration_h_by_date", {}) if isinstance(daily_trends, dict) else {}
    raw_daily_calories = daily_trends.get("calories_by_date", {}) if isinstance(daily_trends, dict) else {}
    raw_daily_intensity = daily_trends.get("intensity_minutes_by_date", {}) if isinstance(daily_trends, dict) else {}
    raw_daily_rhr = daily_trends.get("resting_heart_rate_by_date", {}) if isinstance(daily_trends, dict) else {}
    raw_daily_weight = daily_trends.get("weight_kg_by_date", {}) if isinstance(daily_trends, dict) else {}
    raw_daily_body_age = daily_trends.get("body_age_by_date", {}) if isinstance(daily_trends, dict) else {}
    daily_duration_by_date = _normalize_daily_map(raw_daily_duration)
    daily_calories_by_date = _normalize_daily_map(raw_daily_calories)
    daily_intensity_by_date = _normalize_daily_map(raw_daily_intensity)
    daily_resting_heart_rate_by_date = _normalize_daily_map(raw_daily_rhr)
    daily_weight_kg_by_date = _normalize_daily_map(raw_daily_weight)
    daily_body_age_by_date = _normalize_daily_map(raw_daily_body_age)
    weekly_intensity_minutes = _build_weekly_intensity_minutes_series(
        year=year,
        intensity_minutes_by_date=daily_intensity_by_date,
        goal_minutes=200.0,
    )

    previous_year = year - 1
    prev_monthly = previous_analysis_data.get("monthly_trends", {}) if isinstance(previous_analysis_data, dict) else {}
    prev_meta = previous_analysis_data.get("meta", {}) if isinstance(previous_analysis_data, dict) else {}
    prev_year_meta = prev_meta.get("year")
    if isinstance(prev_year_meta, int):
        previous_year = prev_year_meta
    _, prev_distance_m = _month_series(prev_monthly.get("distance_m_by_month") if isinstance(prev_monthly, dict) else {})
    _, prev_activity_count = _month_series(prev_monthly.get("activity_count_by_month") if isinstance(prev_monthly, dict) else {})
    prev_distance_km = [round(v / 1000.0, 3) for v in prev_distance_m]

    comparison_rows = []
    comparison_rows.extend(
        _change_rows(
            activity_overview.get("change_vs_previous_year"),
            {
                "total_activities": "活动总数",
                "active_days": "活跃天数",
                "total_distance_m": "总距离",
                "total_duration_s": "总时长",
                "total_calories": "总卡路里",
                "total_elevation_gain_m": "总爬升",
            },
            {
                "total_activities": "次",
                "active_days": "天",
                "total_distance_m": "m",
                "total_duration_s": "s",
                "total_calories": "kcal",
                "total_elevation_gain_m": "m",
            },
            "年度概览",
        )
    )
    comparison_rows.extend(
        _change_rows(
            health_overview.get("change_vs_previous_year"),
            {
                "total_steps": "总步数",
                "avg_daily_steps": "日均步数",
                "avg_sleep_hours": "平均睡眠时长",
                "avg_sleep_score": "平均睡眠分数",
                "avg_daily_intensity_minutes": "日均强度分钟",
            },
            {
                "total_steps": "步",
                "avg_daily_steps": "步",
                "avg_sleep_hours": "h",
                "avg_sleep_score": "分",
                "avg_daily_intensity_minutes": "min",
            },
            "健康指标",
        )
    )
    comparison_rows.extend(
        _change_rows(
            run_stats.get("change_vs_previous_year"),
            {
                "count": "跑步次数",
                "total_distance_m": "跑步距离",
                "avg_pace_min_per_km": "跑步配速",
            },
            {
                "count": "次",
                "total_distance_m": "m",
                "avg_pace_min_per_km": "min/km",
            },
            "跑步",
        )
    )
    comparison_rows.extend(
        _change_rows(
            swim_stats.get("change_vs_previous_year"),
            {
                "count": "游泳次数",
                "total_distance_m": "游泳距离",
                "avg_pace_min_per_100m": "游泳配速",
            },
            {
                "count": "次",
                "total_distance_m": "m",
                "avg_pace_min_per_100m": "min/100m",
            },
            "游泳",
        )
    )
    comparison_rows.extend(
        _change_rows(
            strength_stats.get("change_vs_previous_year"),
            {
                "count": "力量训练次数",
                "total_duration_s": "力量训练时长",
                "total_calories": "力量训练卡路里",
                "total_sets": "力量训练总组数",
                "total_reps": "力量训练总次数",
            },
            {
                "count": "次",
                "total_duration_s": "s",
                "total_calories": "kcal",
                "total_sets": "组",
                "total_reps": "次",
            },
            "力量训练",
        )
    )
    comparison_rows.extend(
        _change_rows(
            badminton_stats.get("change_vs_previous_year"),
            {
                "count": "羽毛球次数",
                "total_duration_s": "羽毛球时长",
                "total_distance_m": "羽毛球距离",
                "total_calories": "羽毛球卡路里",
            },
            {
                "count": "次",
                "total_duration_s": "s",
                "total_distance_m": "m",
                "total_calories": "kcal",
            },
            "羽毛球",
        )
    )

    return {
        "year": year,
        "previous_year": previous_year,
        "generated_at": str(date.today()),
        "meta": analysis_data.get("meta", {}) if isinstance(analysis_data, dict) else {},
        "activity_overview": activity_overview,
        "health_overview": health_overview,
        "health_advanced": health_advanced,
        "sports": {
            "running": run_stats,
            "swimming": swim_stats,
            "type_analysis": {
                "labels": sport_labels,
                "by_count": sport_count,
                "by_duration_h": sport_duration_h,
                "by_calories": sport_calories,
                "by_distance_km": sport_distance_km,
                "by_intensity_minutes": sport_intensity_minutes,
                "display_names_zh": display_map,
            },
        },
        "monthly_trends": {
            "labels": month_labels,
            "distance_km": distance_km,
            "activity_count": activity_count,
            "steps_by_month": steps_by_month,
            "sleep_hours_by_month": sleep_hours_by_month,
        },
        "daily_trends": {
            "duration_h_by_date": daily_duration_by_date,
            "calories_by_date": daily_calories_by_date,
            "intensity_minutes_by_date": daily_intensity_by_date,
            "resting_heart_rate_by_date": daily_resting_heart_rate_by_date,
            "weight_kg_by_date": daily_weight_kg_by_date,
            "body_age_by_date": daily_body_age_by_date,
        },
        "weekly_intensity_minutes": weekly_intensity_minutes,
        "previous_monthly_trends": {
            "distance_km": prev_distance_km,
            "activity_count": prev_activity_count,
        },
        "tables": {
            "running_top": _top_activity_rows(run_stats.get("top_activities_by_duration"), include_type=False),
            "swimming_top": _top_activity_rows(swim_stats.get("top_activities_by_duration"), include_type=False),
            "top_activities": _top_activity_rows(activity_overview.get("top_activities_by_duration"), include_type=True),
        },
        "comparison_rows": comparison_rows,
    }


def summarize_totals_from_analysis(analysis_data: dict[str, Any]) -> tuple[int, float, float]:
    overview = analysis_data.get("activity_overview", {}) if isinstance(analysis_data, dict) else {}
    total_activities = int(_as_float(overview.get("total_activities"), 0.0))
    total_km = _as_float(overview.get("total_distance_m"), 0.0) / 1000.0
    total_hours = _as_float(overview.get("total_duration_s"), 0.0) / 3600.0
    return total_activities, total_km, total_hours


def build_html_report_from_analysis(
    analysis_data: dict,
    out_path: Path,
    year: int,
    previous_analysis_data: dict[str, Any] | None = None,
):
    report_data = _build_report_payload_from_analysis(
        analysis_data=analysis_data if isinstance(analysis_data, dict) else {},
        year=year,
        previous_analysis_data=previous_analysis_data if isinstance(previous_analysis_data, dict) else None,
    )
    report_data_json = json.dumps(report_data, ensure_ascii=False)

    template = load_redesign_report_template()
    report_css = load_redesign_report_css()
    report_js = load_redesign_report_js()

    html = (
        template.replace("__YEAR__", str(year))
        .replace("__PREV_YEAR__", str(report_data.get("previous_year", year - 1)))
        .replace("__GENERATED_AT__", str(date.today()))
        .replace("__REPORT_CSS__", report_css)
        .replace("__REPORT_JS__", report_js)
        .replace("__REPORT_DATA_JSON__", report_data_json)
    )
    out_path.write_text(html, encoding="utf-8")
    print(f"✓ HTML报告已生成: {out_path}")


def build_html_report(df: pd.DataFrame, health_stats: dict, plots: dict, out_path: Path, year: int):
    """
    生成HTML报告
    
    Args:
        df: 活动数据DataFrame
        health_stats: 健康数据统计
        plots: 图表文件字典
        out_path: 输出文件路径
        year: 年份
    """
    # 活动统计
    total_acts = int(df["activityId"].nunique())
    total_km = float(df["distance_km"].fillna(0).sum())
    total_h = float(df["duration_h"].fillna(0).sum())
    total_cal = float(df["calories"].fillna(0).sum()) if "calories" in df.columns else 0
    total_elev = float(df["elevGain_m"].fillna(0).sum()) if "elevGain_m" in df.columns else 0

    # 平均配速 (min/km) - 仅计算跑步类
    running_keywords = ("running", "trail", "treadmill", "跑步")
    pace_vals = []
    for _, r in df.iterrows():
      type_str = str(r.get("type") or "").lower()
      if not any(k in type_str for k in running_keywords):
        continue
      d_km = r.get("distance_km") or 0
      dur_s = r.get("duration_s") or 0
      if d_km and d_km > 0 and dur_s and dur_s > 0:
        pace_vals.append((dur_s / 60.0) / d_km)
    avg_pace = sum(pace_vals) / len(pace_vals) if pace_vals else None

    # top 10 最长活动
    top_long = (
        df.sort_values("duration_s", ascending=False)
        .head(10)[["startTimeLocal", "type", "name", "distance_km", "duration_h"]]
    )

    # 构建top活动表格
    top_rows = ""
    for _, row in top_long.iterrows():
        top_rows += f"""
        <tr>
          <td>{row['startTimeLocal']}</td>
          <td>{row['type']}</td>
          <td>{row['name']}</td>
          <td>{row['distance_km']:.2f} km</td>
          <td>{row['duration_h']:.2f} h</td>
        </tr>
        """

    # 活动类型统计（用于扇形图）
    type_stats = (
      df.groupby("type").agg(
        count=("activityId", "nunique"),
        total_distance=("distance_km", "sum"),
        total_hours=("duration_h", "sum"),
        total_calories=("calories", "sum"),
      )
      .sort_values("total_hours", ascending=False)
    )

    # 跑步与游泳章节数据
    def _filter_by_type(keywords):
      return df[df["type"].astype(str).str.lower().str.contains("|".join(keywords), regex=True, na=False)]

    run_df = _filter_by_type(["running", "trail", "treadmill", "跑步"])
    swim_df = _filter_by_type(["swim", "swimming", "pool", "openwater", "游泳"])

    def _summary_stats(sdf: pd.DataFrame):
      if sdf.empty:
        return {
          "count": 0,
          "total_km": 0.0,
          "total_h": 0.0,
          "avg_pace": None,
          "avg_pace_100m": None,
        }
      total_km = float(sdf["distance_km"].fillna(0).sum())
      total_h = float(sdf["duration_h"].fillna(0).sum())
      # 平均配速 min/km
      pace_vals = []
      pace_100m_vals = []
      for _, r in sdf.iterrows():
        d_km = r.get("distance_km") or 0
        dur_s = r.get("duration_s") or 0
        if d_km and d_km > 0 and dur_s and dur_s > 0:
          pace_vals.append((dur_s / 60.0) / d_km)
          pace_100m_vals.append((dur_s / 60.0) / (d_km * 10.0))
      avg_pace = sum(pace_vals) / len(pace_vals) if pace_vals else None
      return {
        "count": int(sdf["activityId"].nunique()),
        "total_km": total_km,
        "total_h": total_h,
        "avg_pace": avg_pace,
        "avg_pace_100m": sum(pace_100m_vals) / len(pace_100m_vals) if pace_100m_vals else None,
      }

    run_stats = _summary_stats(run_df)
    swim_stats = _summary_stats(swim_df)

    run_avg_pace_str = f"{run_stats['avg_pace']:.2f} min/km" if run_stats["avg_pace"] else "N/A"
    swim_avg_pace_str = f"{swim_stats['avg_pace_100m']:.2f} min/100m" if swim_stats["avg_pace_100m"] else "N/A"

    run_top = run_df.sort_values("duration_s", ascending=False).head(5)[
      ["startTimeLocal", "name", "distance_km", "duration_h"]
    ] if not run_df.empty else pd.DataFrame(columns=["startTimeLocal", "name", "distance_km", "duration_h"])
    swim_top = swim_df.sort_values("duration_s", ascending=False).head(5)[
      ["startTimeLocal", "name", "distance_km", "duration_h"]
    ] if not swim_df.empty else pd.DataFrame(columns=["startTimeLocal", "name", "distance_km", "duration_h"])

    # Plotly 图表
    plotly_charts = build_plotly_charts(df, year)

    # 活动类型 3D 扇形图（以 Plotly Pie 近似 3D 效果）
    def _pie_html(values, labels, title):
      if not values:
        fig = go.Figure()
        fig.add_annotation(text="暂无数据", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=360, margin=dict(l=40, r=20, t=50, b=40))
        return fig.to_html(include_plotlyjs=False, full_html=False)
      fig = go.Figure(
        data=[
          go.Pie(
            labels=labels,
            values=values,
            hole=0.35,
            pull=[0.02] * len(values),
            textinfo="percent+label",
            textposition="outside",
          )
        ]
      )
      fig.update_layout(
        title=title,
        height=360,
        margin=dict(l=40, r=20, t=50, b=40),
      )
      return fig.to_html(include_plotlyjs=False, full_html=False)

    type_labels = type_stats.index.astype(str).tolist()
    count_values = type_stats["count"].fillna(0).astype(float).tolist()
    hour_values = type_stats["total_hours"].fillna(0).astype(float).tolist()
    cal_values = type_stats["total_calories"].fillna(0).astype(float).tolist()

    type_pie_count = _pie_html(count_values, type_labels, "各运动类型次数占比")
    type_pie_hours = _pie_html(hour_values, type_labels, "各运动类型总时长占比")
    type_pie_calories = _pie_html(cal_values, type_labels, "各运动类型总卡路里占比")

    # 健康数据卡片
    health_card = ""
    if health_stats:
        sleep_stats = health_stats.get('sleep', {})
        steps_stats = health_stats.get('steps', {})
        hrv_stats = health_stats.get('hrv', {})
        intensity_stats = health_stats.get('intensity', {})
        
        health_card = f"""
  <div class=\"card\">
    <h2>💤 健康数据统计</h2>
    <div class=\"kpis\">
      <div class=\"kpi\">
        <div class=\"kpi-label\">睡眠记录天数</div>
        <div class=\"kpi-value\">{sleep_stats.get('count', 0)} 天</div>
      </div>
      <div class=\"kpi\">
        <div class=\"kpi-label\">平均睡眠时长</div>
        <div class=\"kpi-value\">{sleep_stats.get('avg_duration', 0):.1f} 小时</div>
      </div>
      <div class=\"kpi\">
        <div class=\"kpi-label\">平均睡眠分数</div>
        <div class=\"kpi-value\">{sleep_stats.get('avg_sleep_score', 0):.1f}</div>
      </div>
      <div class=\"kpi\">
        <div class=\"kpi-label\">平均深度睡眠</div>
        <div class=\"kpi-value\">{sleep_stats.get('avg_deep_sleep', 0):.1f} 小时</div>
      </div>
      <div class=\"kpi\">
        <div class=\"kpi-label\">总步数</div>
        <div class=\"kpi-value\">{steps_stats.get('total', 0):,} 步</div>
      </div>
      <div class=\"kpi\">
        <div class=\"kpi-label\">平均每日步数</div>
        <div class=\"kpi-value\">{steps_stats.get('avg_daily', 0):,.0f} 步</div>
      </div>
      <div class=\"kpi\">
        <div class=\"kpi-label\">HRV记录天数</div>
        <div class=\"kpi-value\">{hrv_stats.get('count', 0)} 天</div>
      </div>
      <div class=\"kpi\">
        <div class=\"kpi-label\">平均每日强度活动分钟数</div>
        <div class=\"kpi-value\">{intensity_stats.get('avg_daily', 0):.1f} 分钟</div>
      </div>
    </div>
  </div>
        """

    html = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Garmin 年度报告 {year}</title>
  <script src=\"https://cdn.plot.ly/plotly-2.30.0.min.js\"></script>
  <style>
    :root {{ --bg:#f6f8fb; --card:#fff; --muted:#6b7280; --accent:#2563eb; }}
    body {{ 
      font-family: -apple-system,BlinkMacSystemFont,\"Segoe UI\",Roboto,Arial,\"PingFang SC\",\"Hiragino Sans GB\",\"Microsoft YaHei\",sans-serif; 
      margin: 0;
      padding: 24px;
      background: var(--bg);
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      background: white;
      padding: 32px;
      border-radius: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .card {{ 
      border: 1px solid #eee; 
      border-radius: 12px; 
      padding: 24px; 
      margin: 24px 0;
      background: #fafafa;
    }}
    .kpis {{ 
      display: grid; 
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
      gap: 16px;
      margin-top: 16px;
    }}
    .kpi {{ 
      background: white; 
      border-radius: 12px; 
      padding: 20px;
      text-align: center;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    .kpi-label {{
      color: #666;
      font-size: 14px;
      margin-bottom: 8px;
    }}
    .kpi-value {{
      color: #1a1a1a;
      font-size: 28px;
      font-weight: 600;
    }}
    h1 {{ 
      margin: 0 0 8px 0;
      font-size: 32px;
      color: #1a1a1a;
    }}
    h2 {{ 
      margin: 0 0 16px 0;
      font-size: 24px;
      color: #1a1a1a;
    }}
    img {{ 
      max-width: 100%; 
      border-radius: 12px; 
      margin: 16px 0;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}
    table {{ 
      width: 100%; 
      border-collapse: collapse;
      margin-top: 16px;
      background: white;
    }}
    th, td {{ 
      padding: 12px; 
      border-bottom: 1px solid #eee; 
      text-align: left;
    }}
    th {{
      background: #f5f5f5;
      font-weight: 600;
      color: #1a1a1a;
    }}
    .muted {{ 
      color: #666;
      font-size: 14px;
    }}
    .header {{
      border-bottom: 2px solid #eee;
      padding-bottom: 24px;
      margin-bottom: 24px;
    }}
    .charts {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }}
  </style>
</head>
<body>
  <div class=\"container\">
    <div class=\"header\">
      <h1>🏃 Garmin 年度报告 - {year}</h1>
      <p class=\"muted\">数据来源：Garmin Connect | 生成时间：{date.today()}</p>
    </div>

    <div class=\"card\">
      <h2>📊 核心数据</h2>
      <div class=\"kpis\">
        <div class=\"kpi\">
          <div class=\"kpi-label\">活动总数</div>
          <div class=\"kpi-value\">{total_acts}</div>
        </div>
        <div class=\"kpi\">
          <div class=\"kpi-label\">总距离</div>
          <div class=\"kpi-value\">{total_km:.1f} km</div>
        </div>
        <div class=\"kpi\">
          <div class=\"kpi-label\">总时长</div>
          <div class=\"kpi-value\">{total_h:.1f} h</div>
        </div>
        <div class=\"kpi\">
          <div class=\"kpi-label\">总卡路里</div>
          <div class=\"kpi-value\">{total_cal:,.0f}</div>
        </div>
        <div class=\"kpi\">
          <div class=\"kpi-label\">总爬升</div>
          <div class=\"kpi-value\">{total_elev:.0f} m</div>
        </div>
      </div>
    </div>

{health_card}

    <div class=\"card\">
      <h2>🏃 跑步统计</h2>
      <div class=\"kpis\">
        <div class=\"kpi\"><div class=\"kpi-label\">跑步次数</div><div class=\"kpi-value\">{run_stats['count']}</div></div>
        <div class=\"kpi\"><div class=\"kpi-label\">总距离</div><div class=\"kpi-value\">{run_stats['total_km']:.1f} km</div></div>
        <div class=\"kpi\"><div class=\"kpi-label\">总时长</div><div class=\"kpi-value\">{run_stats['total_h']:.1f} h</div></div>
        <div class=\"kpi\"><div class=\"kpi-label\">平均配速</div><div class=\"kpi-value\">{run_avg_pace_str}</div></div>
      </div>
      <div style=\"margin-top:12px\"></div>
      <h3 style=\"margin:0 0 8px 0\">Top 5 最长跑步</h3>
      {run_top.to_html(index=False, border=0)}
    </div>

    <div class=\"card\">
      <h2>🏊 游泳统计</h2>
      <div class=\"kpis\">
        <div class=\"kpi\"><div class=\"kpi-label\">游泳次数</div><div class=\"kpi-value\">{swim_stats['count']}</div></div>
        <div class=\"kpi\"><div class=\"kpi-label\">总距离</div><div class=\"kpi-value\">{swim_stats['total_km']:.1f} km</div></div>
        <div class=\"kpi\"><div class=\"kpi-label\">总时长</div><div class=\"kpi-value\">{swim_stats['total_h']:.1f} h</div></div>
        <div class=\"kpi\"><div class=\"kpi-label\">平均配速</div><div class=\"kpi-value\">{swim_avg_pace_str}</div></div>
      </div>
      <div style=\"margin-top:12px\"></div>
      <h3 style=\"margin:0 0 8px 0\">Top 5 最长游泳</h3>
      {swim_top.to_html(index=False, border=0)}
    </div>

    <div class=\"card\">
      <h2>🧊 活动时长 3D 热力图</h2>
      {plotly_charts['duration_heatmap_3d']}
    </div>

    <div class=\"card\">
      <h2>🔥 卡路里消耗 3D 热力图</h2>
      {plotly_charts['calories_heatmap_3d']}
    </div>

    <div class=\"card\">
      <h2>🥧 运动类型分析</h2>
      <div class=\"charts\">
        {type_pie_count}
        {type_pie_hours}
        {type_pie_calories}
      </div>
    </div>

    <div class=\"card\">
      <h2>🏆 Top 10 最长活动</h2>
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>类型</th>
            <th>名称</th>
            <th>距离</th>
            <th>时长</th>
          </tr>
        </thead>
        <tbody>
{top_rows}
        </tbody>
      </table>
    </div>

    <div class=\"muted\" style=\"text-align: center; margin-top: 32px; padding-top: 24px; border-top: 1px solid #eee;\">
      <p>由 Garmin 数据分析工具自动生成</p>
    </div>
  </div>
</body>
</html>
"""

    out_path.write_text(html, encoding="utf-8")
    print(f"✓ HTML报告已生成: {out_path}")


def main():
    """主函数：处理参数并生成报告"""
    parser = argparse.ArgumentParser(description='生成Garmin年度分析报告')
    parser.add_argument('--year', type=int, help='年份（默认：去年）')
    parser.add_argument('--data-dir', help='数据目录（默认: garmin_report_YEAR）')
    
    args = parser.parse_args()
    
    year = args.year or (date.today().year - 1)
    data_dir = Path(args.data_dir or f"garmin_report_{year}")
    
    # 检查数据目录
    if not data_dir.exists():
        print(f"❌ 错误: 数据目录不存在: {data_dir}")
        print(f"请先运行: python fetch_garmin_data.py --year {year}")
        return
    
    activities_file = data_dir / "data" / f"activities_{year}.json"
    health_file = data_dir / "data" / f"health_data_{year}.json"

    print("="*60)
    print(f"Garmin 报告生成工具")
    print("="*60)
    print(f"年份: {year}")
    print(f"数据目录: {data_dir.resolve()}")
    print("="*60)

    analysis_data = None
    analysis_path = None
    print("\n正在读取分析数据...")
    try:
        analysis_data, analysis_path = load_analysis_report(data_dir=data_dir)
        print(f"✓ 已读取分析数据: {analysis_path}")
    except Exception:
        print("⚠ 未找到分析数据，正在自动生成 analyze_report_data.json ...")
        try:
            analysis_data, analysis_path = build_analysis_report(year=year, data_dir=data_dir)
            print(f"✓ 分析数据生成完成: {analysis_path}")
        except Exception as e:
            print(f"⚠ 分析数据生成失败，将回退到原始活动数据模式: {e}")

    report_path = data_dir / f"report_{year}.html"
    if isinstance(analysis_data, dict):
        previous_analysis_data: dict[str, Any] | None = None
        previous_year = year - 1
        previous_dir = data_dir.parent / f"garmin_report_{previous_year}"
        if previous_dir.exists():
            try:
                previous_analysis_data, previous_path = load_analysis_report(data_dir=previous_dir)
                print(f"✓ 已读取上一年分析数据: {previous_path}")
            except Exception as e:
                print(f"⚠ 读取上一年分析数据失败，继续生成当前年度报告: {e}")

        print("\n正在基于分析数据生成HTML报告...")
        build_html_report_from_analysis(
            analysis_data=analysis_data,
            out_path=report_path,
            year=year,
            previous_analysis_data=previous_analysis_data,
        )
        total_activities, total_km, total_hours = summarize_totals_from_analysis(analysis_data)
    else:
        if not activities_file.exists():
            print(f"❌ 错误: 活动数据文件不存在，且分析数据不可用: {activities_file}")
            print(f"请先运行: python analyze_report_data.py --year {year}")
            return

        print("\n正在读取活动数据...")
        try:
            activities = json.loads(activities_file.read_text(encoding="utf-8"))
            print(f"✓ 读取到 {len(activities)} 条活动记录")
        except Exception as e:
            print(f"✗ 读取活动数据失败: {e}")
            return

        health_data = {}
        health_stats = {}
        if health_file.exists():
            print("正在读取健康数据...")
            try:
                health_data = json.loads(health_file.read_text(encoding="utf-8"))
                health_stats = analyze_health_data(health_data, year)
                print(f"✓ 健康数据读取完成")
                print(f"  - 睡眠记录: {health_stats['sleep'].get('count', 0)} 天")
                print(f"  - 步数记录: {health_stats['steps'].get('count', 0)} 天")
                print(f"  - HRV记录: {health_stats['hrv'].get('count', 0)} 天")
            except Exception as e:
                print(f"⚠ 读取健康数据失败: {e}")

        print("\n正在规范化数据...")
        df = normalize_activities(activities)
        print(f"✓ 规范化后的数据: {len(df)} 行")
        if len(df) > 0:
            print(f"  日期范围: {df['date'].min()} 到 {df['date'].max()}")
            print(f"  运动类型: {df['type'].nunique()} 种")

        print("\n正在生成图表...")
        plot_dir = data_dir / "plots"
        plots = make_plots(df, plot_dir, year)
        print(f"✓ 图表已生成到: {plot_dir}")

        print("\n正在生成HTML报告...")
        build_html_report(df, health_stats, plots, report_path, year)
        total_activities = len(df)
        total_km = float(df['distance_km'].sum())
        total_hours = float(df['duration_h'].sum())

    print(f"\n{'='*60}")
    print(f"✅ 报告生成完成！")
    print(f"{'='*60}")
    print(f"报告路径: {report_path.resolve()}")
    print(f"活动总数: {total_activities}")
    print(f"总距离: {total_km:.1f} km")
    print(f"总时长: {total_hours:.1f} h")
    print(f"数据目录: {data_dir.resolve()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
