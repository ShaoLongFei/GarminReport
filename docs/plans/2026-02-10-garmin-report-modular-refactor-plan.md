# Garmin Report Modular Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `generate_report.py` 的重型前端模板逐步拆分为可维护结构（模板、样式、脚本分层），在每一步保持功能等价并可快速回滚。

**Architecture:** 采用“三阶段、每阶段可独立发布”的低风险策略：先抽离 HTML 模板文件，再抽离 CSS/JS 文件并通过占位符注入，最后把前端脚本按职责拆分模块并补回归测试。每阶段都执行 Red/Green 验证并以现有报告生成为验收标准。

**Tech Stack:** Python 3.14、unittest、现有 Alpine.js + ECharts + Obelisk 前端渲染。

---

### Task 1: 抽离重构版 HTML 模板（本轮已完成）

**Files:**
- Create: `templates/redesign_report_template.html`
- Modify: `generate_report.py`
- Test: `tests/test_generate_report.py`

**Step 1: Write the failing test**

```python
def test_load_redesign_report_template_contains_placeholders(self):
    template = load_redesign_report_template()
    self.assertIn("__YEAR__", template)
    self.assertIn("__REPORT_DATA_JSON__", template)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_generate_report.GenerateReportAnalysisLoadTests.test_load_redesign_report_template_contains_placeholders -v`
Expected: `ImportError` / missing function.

**Step 3: Write minimal implementation**

- 在 `generate_report.py` 新增 `load_redesign_report_template()`。
- 将 `build_html_report_from_analysis` 的内联模板替换为文件加载。

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_generate_report -v`
Expected: 全部 PASS。

**Step 5: Commit**

```bash
git add templates/redesign_report_template.html generate_report.py tests/test_generate_report.py docs/plans/2026-02-10-garmin-report-modular-refactor-plan.md
git commit -m "refactor: extract redesigned HTML template to external file"
```

### Task 2: 抽离 CSS 为独立文件并注入模板

**Files:**
- Create: `templates/assets/report_redesign.css`
- Modify: `templates/redesign_report_template.html`
- Modify: `generate_report.py`
- Test: `tests/test_generate_report.py`

**Step 1: Write the failing test**

- 新增断言 HTML 输出包含外链/注入标记（如 `report_redesign.css` 标识或 `__REPORT_CSS__` 占位符替换结果）。

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_generate_report.GenerateReportAnalysisLoadTests.test_report_from_analysis_contains_redesigned_dark_dashboard_payload -v`

**Step 3: Write minimal implementation**

- 将 `<style>...</style>` 内容迁移到 CSS 文件。
- 模板保留占位符，由 Python 注入或读取 CSS 内容拼装。

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_generate_report -v`

**Step 5: Commit**

```bash
git add templates/assets/report_redesign.css templates/redesign_report_template.html generate_report.py tests/test_generate_report.py
git commit -m "refactor: extract redesigned report css"
```

### Task 3: 抽离 JS 为独立文件并保持行为一致

**Files:**
- Create: `templates/assets/report_redesign.js`
- Modify: `templates/redesign_report_template.html`
- Modify: `generate_report.py`
- Test: `tests/test_generate_report.py`

**Step 1: Write the failing test**

- 断言渲染脚本仍包含关键行为标记：`setIsoViewMode`、`window.print()`、`ensureSports3DContributionCharts`。

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_generate_report.GenerateReportAnalysisLoadTests.test_report_from_analysis_contains_redesigned_dark_dashboard_payload -v`

**Step 3: Write minimal implementation**

- 将 `<script>...</script>` 的业务逻辑迁移到 `report_redesign.js`。
- 保留数据注入点：`window.REPORT_DATA = __REPORT_DATA_JSON__`。

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_generate_report -v`

**Step 5: Commit**

```bash
git add templates/assets/report_redesign.js templates/redesign_report_template.html generate_report.py tests/test_generate_report.py
git commit -m "refactor: extract redesigned report javascript"
```

### Task 4: 增加模板加载回归保护与文件存在性校验

**Files:**
- Modify: `generate_report.py`
- Test: `tests/test_generate_report.py`

**Step 1: Write the failing test**

- 缺失模板文件时抛出明确错误（`FileNotFoundError` 消息包含路径）。

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_generate_report -v`

**Step 3: Write minimal implementation**

- 增加缓存加载、错误提示与必要的路径常量。

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_generate_report -v`

**Step 5: Commit**

```bash
git add generate_report.py tests/test_generate_report.py
git commit -m "test: add template loading regression safeguards"
```
