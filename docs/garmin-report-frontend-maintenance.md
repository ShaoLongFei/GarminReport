# Garmin 年报前端维护说明

本文档用于说明 `build_html_report_from_analysis` 的前端资源结构，方便后续迭代功能和修复问题。

## 文件结构

- Python 入口：`generate_report.py`
- HTML 模板：`templates/redesign_report_template.html`
- CSS 样式：`templates/assets/report_redesign.css`
- JS 逻辑：`templates/assets/report_redesign.js`

## 渲染流程

`generate_report.py` 通过以下函数加载前端资源并注入到 HTML：

- `load_redesign_report_template()`
- `load_redesign_report_css()`
- `load_redesign_report_js()`

模板中的占位符：

- `__YEAR__`
- `__PREV_YEAR__`
- `__GENERATED_AT__`
- `__REPORT_CSS__`
- `__REPORT_JS__`
- `__REPORT_DATA_JSON__`

最终输出文件：

- `garmin_report_<year>/report_<year>.html`

## 常见改动入口

1. 改页面结构
- 修改 `templates/redesign_report_template.html`
- 仅做结构和占位符相关调整，避免把大量样式/逻辑写回模板

2. 改视觉样式
- 修改 `templates/assets/report_redesign.css`
- 优先使用已有 class，避免在模板里增加大量 inline style

3. 改交互逻辑（图表、导出 PDF、2D/3D/Both 切换）
- 修改 `templates/assets/report_redesign.js`
- 与数据结构相关的字段变更，同时检查 `generate_report.py` 的 payload 构建逻辑

4. 改数据字段/统计口径
- 修改 `generate_report.py` 中：
  - `_build_report_payload_from_analysis(...)`
  - 相关分析聚合函数
- 同步检查 JS 中 `window.REPORT_DATA` 的消费字段

## 健康洞察降级规则

- 身体年龄图表使用 `daily_trends.body_age_by_date` 作为数据源。
- 当 `body_age_by_date` 为空时：
  - 自动移除“身体年龄变化记录”图表面板。
  - 将“体重变化记录”和“静息心率变化记录”扩展为两栏布局（各占半行）。
- 这是预期行为，不应显示空白身体年龄图表，以避免误判为渲染故障。

## 低风险改动建议

- 一次只改一个层面：结构 / 样式 / 脚本 / 数据口径
- 先改测试再改实现（尤其是字段和交互）
- 保持占位符命名稳定，减少模板注入回归风险

## 回归检查命令

1. 单元测试

```bash
python3 -m unittest tests.test_generate_report -v
```

2. 生成真实报告

```bash
python3 generate_report.py --year 2025
```

3. 可选截图回归（Playwright）

```bash
npx playwright screenshot --full-page --wait-for-timeout 2500 \
  --viewport-size "1366,900" \
  "file:///ABS_PATH/garmin_report_2025/report_2025.html?tab=sports&isoView=both" \
  output/playwright/desktop-sports-regression.png
```

## 故障排查

若出现模板/样式/脚本加载失败，当前实现会抛出明确路径错误：

- `报告模板不存在: ...`
- `报告样式不存在: ...`
- `报告脚本不存在: ...`

优先检查：

- 目标文件是否存在
- 路径是否被移动
- 是否在非项目根目录下运行脚本

## 发布前检查清单

每次准备交付前，建议按顺序执行：

1. 变更范围自检
- 只改了预期文件（模板 / CSS / JS / Python 数据层）
- 没有把临时调试代码、日志、测试截图误提交到主代码路径

2. 占位符完整性检查
- `templates/redesign_report_template.html` 仍包含：
  - `__REPORT_CSS__`
  - `__REPORT_JS__`
  - `__REPORT_DATA_JSON__`
- 变更后没有引入拼写错误或删除关键占位符

3. 自动化测试

```bash
python3 -m unittest tests.test_generate_report -v
```

4. 实际生成功能检查

```bash
python3 generate_report.py --year 2025
```

- 确认输出文件存在：`garmin_report_2025/report_2025.html`
- 打开页面确认：标签切换、2D/3D/Both 切换、导出打印按钮可用

5. 快速视觉回归（建议）

```bash
npx playwright screenshot --full-page --wait-for-timeout 2500 \
  --viewport-size "1366,900" \
  "file:///ABS_PATH/garmin_report_2025/report_2025.html?tab=sports&isoView=both" \
  output/playwright/desktop-sports-release-check.png
```

- 重点看：图表是否空白、是否裁切、字号颜色是否异常、布局是否溢出

6. 异常路径抽查（可选）
- 临时重命名模板或样式文件，确认错误提示是否清晰（含完整路径）
- 验证后恢复文件名
