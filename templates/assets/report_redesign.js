(function initReport() {
      const report = window.REPORT_DATA || {};
      const chartRefs = [];
      const customResizers = {};
      const toastEl = document.getElementById('share-toast');
      let toastTimer = null;
      let resizeRaf = 0;

      function getChartTheme() {
        return {
          textStyle: { color: '#dbe7ff' },
          grid: { left: 48, right: 30, top: 40, bottom: 40 },
          tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(7, 16, 38, 0.95)',
            borderColor: 'rgba(100, 153, 255, 0.3)',
            textStyle: { color: '#f4f8ff' }
          },
          legend: { textStyle: { color: '#bdd2ff' } },
          xAxis: {
            axisLabel: { color: '#90a8db' },
            axisLine: { lineStyle: { color: 'rgba(116, 153, 224, 0.4)' } },
            axisTick: { show: false },
          },
          yAxis: {
            axisLabel: { color: '#90a8db' },
            splitLine: { lineStyle: { color: 'rgba(116, 153, 224, 0.16)' } },
            axisLine: { show: false },
          }
        };
      }

      function fmtNumber(v, digits) {
        const n = Number(v || 0);
        return n.toLocaleString(undefined, {
          minimumFractionDigits: digits,
          maximumFractionDigits: digits
        });
      }

      function fmtPct(v) {
        const n = Number(v || 0);
        return (n >= 0 ? '+' : '') + n.toFixed(2) + '%';
      }

      function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
      }

      function setHtml(id, value) {
        const el = document.getElementById(id);
        if (el) el.innerHTML = value;
      }

      function showToast(message, type) {
        if (!toastEl) return;
        toastEl.textContent = message || '';
        toastEl.className = `share-toast show ${type || ''}`.trim();
        if (toastTimer) {
          clearTimeout(toastTimer);
        }
        toastTimer = setTimeout(() => {
          toastEl.className = 'share-toast';
        }, 2200);
      }

      function metricCard(label, value, hint) {
        return `
          <div class="metric-card">
            <div class="metric-label">${label}</div>
            <div class="metric-value">${value}</div>
            ${hint ? `<div class="metric-hint">${hint}</div>` : ''}
          </div>
        `;
      }

      function compactLabel(label) {
        if (!label) return '';
        return label.length > 4 ? label.slice(0, 4) + '…' : label;
      }

      function renderTopCards(rows, includeType) {
        return `
          <div class="activity-cards">
            ${rows.map((row) => `
              <article class="activity-card">
                <div class="activity-line">
                  <div class="activity-name">${row.activity_name || '-'}</div>
                  <div class="activity-date">${row.date || ''}</div>
                </div>
                <div class="activity-meta">
                  ${includeType ? `<span class="activity-pill">${row.type_key || '-'}</span>` : ''}
                  <span class="activity-pill">${fmtNumber(row.distance_km || 0, 2)} km</span>
                  <span class="activity-pill">${fmtNumber(row.duration_h || 0, 2)} h</span>
                </div>
              </article>
            `).join('')}
          </div>
        `;
      }

      function renderTopTable(rows, includeType) {
        if (!Array.isArray(rows) || rows.length === 0) {
          return '<p class="muted-note">暂无数据</p>';
        }
        if (isMobile) {
          return renderTopCards(rows, includeType);
        }
        const typeHead = includeType ? '<th>类型</th>' : '';
        const body = rows.map((row) => `
          <tr>
            <td>${row.date || ''}</td>
            ${includeType ? `<td>${row.type_key || ''}</td>` : ''}
            <td>${row.activity_name || ''}</td>
            <td>${fmtNumber(row.distance_km || 0, 2)} km</td>
            <td>${fmtNumber(row.duration_h || 0, 2)} h</td>
          </tr>
        `).join('');
        return `
          <table>
            <thead>
              <tr>
                <th>日期</th>
                ${typeHead}
                <th>名称</th>
                <th>距离</th>
                <th>时长</th>
              </tr>
            </thead>
            <tbody>${body}</tbody>
          </table>
        `;
      }

      function renderCompareMonthlyIntensityCards(cards) {
        if (!Array.isArray(cards) || cards.length === 0) {
          return '<p class="muted-note">暂无强度活动同比数据</p>';
        }
        return cards.map((card) => {
          const monthLabel = card.month_label || `${String(card.month || '').replace(/^0/, '')}月`;
          const current = Number(card.current_minutes || 0);
          const previous = Number(card.previous_minutes || 0);
          const delta = Number(card.delta_minutes || 0);
          const pctRaw = card.pct_change;
          const hasPct = Number.isFinite(Number(pctRaw));
          const deltaClass = delta > 0 ? 'pos' : (delta < 0 ? 'neg' : 'flat');
          const deltaSign = delta > 0 ? '+' : (delta < 0 ? '-' : '');
          const deltaMinutesText = `${deltaSign}${fmtNumber(Math.abs(delta), 1)} min`;
          return `
            <article class="compare-intensity-card ${deltaClass}">
              <div class="compare-intensity-month">${monthLabel}</div>
              <div class="compare-intensity-label">本月强度活动时间</div>
              <div class="compare-intensity-current">${fmtNumber(current, 1)} min</div>
              <div class="compare-intensity-delta">
                <span>同比 ${deltaMinutesText}</span>
                <span class="compare-intensity-pct ${hasPct ? deltaClass : 'na'}">${hasPct ? fmtPct(pctRaw) : '无可比数据'}</span>
              </div>
              <div class="compare-intensity-prev">上年同月 ${fmtNumber(previous, 1)} min</div>
            </article>
          `;
        }).join('');
      }

      function toIsoDateKey(dt) {
        const y = dt.getFullYear();
        const m = String(dt.getMonth() + 1).padStart(2, '0');
        const d = String(dt.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
      }

      function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
      }

      function normalizeIsoAxisSize(value) {
        let size = Math.max(6, Math.round(Number(value) || 0));
        if (size % 2 !== 0) {
          size -= 1;
        }
        if (size < 6) {
          size = 6;
        }
        return size;
      }

      function normalizeIsoCubeHeight(value) {
        return Math.max(3, Math.round(Number(value) || 0));
      }

      function valueToLevel(value, maxVal) {
        if (!maxVal || value <= 0) return 0;
        const ratio = value / maxVal;
        if (ratio <= 0.2) return 1;
        if (ratio <= 0.45) return 2;
        if (ratio <= 0.7) return 3;
        return 4;
      }

      function hexToRgba(hex, alpha) {
        const safe = String(hex || '').replace('#', '').padStart(6, '0').slice(0, 6);
        const r = Number.parseInt(safe.slice(0, 2), 16) || 0;
        const g = Number.parseInt(safe.slice(2, 4), 16) || 0;
        const b = Number.parseInt(safe.slice(4, 6), 16) || 0;
        return `rgba(${r}, ${g}, ${b}, ${clamp(Number(alpha || 1), 0, 1)})`;
      }

      function buildIsoMonthMarkers(weeks) {
        const markers = [];
        let lastMonth = -1;
        weeks.forEach((week, weekIdx) => {
          const firstDay = week.find((d) => d.date && d.date.slice(8, 10) === '01');
          if (!firstDay) return;
          const dt = new Date(`${firstDay.date}T00:00:00`);
          const month = dt.getMonth();
          if (month === lastMonth) return;
          lastMonth = month;
          markers.push({ weekIdx, label: `${month + 1}月` });
        });
        if (!markers.length) {
          markers.push({ weekIdx: 0, label: '1月' });
        }
        return markers;
      }

      function renderFlatContributionGrid(target, contribution, options) {
        if (!target) return;
        target.innerHTML = '';
        const weeks = Array.isArray(contribution.weeks) ? contribution.weeks : [];
        const weekCount = Math.max(weeks.length, 1);
        const palette = Array.isArray(options.palette) && options.palette.length >= 5
          ? options.palette
          : ['161b22', '0e4429', '006d32', '26a641', '39d353'];
        const unitLabel = options.unitLabel || '';
        const root = document.createElement('div');
        root.className = 'iso-flat-root';

        const months = document.createElement('div');
        months.className = 'iso-flat-months';
        buildIsoMonthMarkers(weeks).forEach((item) => {
          const marker = document.createElement('span');
          marker.className = 'iso-flat-month';
          const leftPct = weekCount <= 1 ? 0 : (item.weekIdx / (weekCount - 1)) * 100;
          marker.style.left = `${leftPct.toFixed(2)}%`;
          marker.textContent = item.label;
          months.appendChild(marker);
        });
        root.appendChild(months);

        const main = document.createElement('div');
        main.className = 'iso-flat-main';
        const dayAxis = document.createElement('div');
        dayAxis.className = 'iso-flat-days';
        ['一', '', '三', '', '五', '', ''].forEach((label) => {
          const el = document.createElement('span');
          el.textContent = label;
          dayAxis.appendChild(el);
        });
        main.appendChild(dayAxis);

        const grid = document.createElement('div');
        grid.className = 'iso-flat-grid';
        grid.style.setProperty('--week-count', String(weekCount));
        weeks.forEach((week, weekIdx) => {
          week.forEach((day, dayIdx) => {
            const cell = document.createElement('div');
            const value = Number(day.value || 0);
            const level = valueToLevel(value, contribution.maxVal);
            const colorHex = palette[level] || palette[0];
            cell.className = 'iso-flat-cell';
            cell.style.gridColumn = String(weekIdx + 1);
            cell.style.gridRow = String(dayIdx + 1);
            if (!day.date) {
              cell.classList.add('empty');
              cell.title = '';
            } else {
              const bg = level === 0
                ? 'rgba(17, 29, 54, 0.86)'
                : hexToRgba(colorHex, 0.92);
              cell.style.background = bg;
              cell.title = `${day.date} ${fmtNumber(value, 2)} ${unitLabel}`;
            }
            grid.appendChild(cell);
          });
        });
        main.appendChild(grid);
        root.appendChild(main);

        const legend = document.createElement('div');
        legend.className = 'iso-flat-legend';
        legend.innerHTML = '<span>Less</span>';
        for (let idx = 0; idx < 5; idx++) {
          const swatch = document.createElement('span');
          swatch.className = 'iso-flat-swatch';
          swatch.style.background = idx === 0
            ? 'rgba(17, 29, 54, 0.86)'
            : hexToRgba(palette[idx], 0.92);
          legend.appendChild(swatch);
        }
        legend.insertAdjacentHTML('beforeend', '<span>More</span>');
        root.appendChild(legend);

        target.appendChild(root);
      }

      function buildIsoContributionData(dailyMap) {
        const targetYear = Number(report.year || new Date().getFullYear());
        const firstDay = new Date(targetYear, 0, 1);
        const lastDay = new Date(targetYear, 11, 31);
        const firstWeekStart = new Date(firstDay);
        firstWeekStart.setDate(firstDay.getDate() - ((firstDay.getDay() + 6) % 7));
        const msWeek = 7 * 24 * 60 * 60 * 1000;

        const byDate = {};
        Object.entries(dailyMap || {}).forEach(([dateText, val]) => {
          const key = String(dateText || '').slice(0, 10);
          const parsed = Number(val || 0);
          if (key) {
            byDate[key] = Number.isFinite(parsed) ? parsed : 0;
          }
        });

        const weeks = [];
        let maxVal = 0;
        let total = 0;
        let bestDay = '';
        let bestValue = 0;
        let dayCount = 0;

        for (let cursor = new Date(firstDay); cursor <= lastDay; cursor.setDate(cursor.getDate() + 1)) {
          const iso = toIsoDateKey(cursor);
          const weekday = (cursor.getDay() + 6) % 7;
          const weekIndex = Math.floor((cursor - firstWeekStart) / msWeek);
          while (weeks.length <= weekIndex) {
            weeks.push(Array.from({ length: 7 }, () => ({ date: '', value: 0 })));
          }
          const value = Number(byDate[iso] || 0);
          const finalValue = Number.isFinite(value) ? value : 0;
          weeks[weekIndex][weekday] = { date: iso, value: finalValue };
          total += finalValue;
          dayCount += 1;
          if (finalValue > maxVal) maxVal = finalValue;
          if (finalValue > bestValue) {
            bestValue = finalValue;
            bestDay = iso;
          }
        }

        let bestWeekTotal = 0;
        weeks.forEach((week) => {
          const weekValue = week.reduce((sum, item) => sum + Number(item.value || 0), 0);
          if (weekValue > bestWeekTotal) {
            bestWeekTotal = weekValue;
          }
        });

        return {
          weeks,
          maxVal,
          total,
          average: dayCount ? total / dayCount : 0,
          bestDay,
          bestValue,
          bestWeekTotal,
        };
      }

      function buildSortedDailySeries(dailyMap) {
        const rows = Object.entries(dailyMap || {})
          .map(([dateText, value]) => {
            const key = String(dateText || '').slice(0, 10);
            if (!key) return null;
            const parsed = Number(value || 0);
            return {
              date: key,
              value: Number.isFinite(parsed) ? parsed : 0,
            };
          })
          .filter(Boolean)
          .sort((a, b) => a.date.localeCompare(b.date));
        return {
          dates: rows.map((item) => item.date),
          values: rows.map((item) => item.value),
        };
      }

      function computeSeriesRange(values, options) {
        const cfg = options || {};
        const pad = Number(cfg.pad || 0);
        const minSpan = Number(cfg.minSpan || 0);
        const precision = Number.isFinite(cfg.precision) ? Math.max(0, cfg.precision) : 2;
        const minClamp = Number.isFinite(cfg.minClamp) ? Number(cfg.minClamp) : null;
        const maxClamp = Number.isFinite(cfg.maxClamp) ? Number(cfg.maxClamp) : null;
        const numericValues = (values || [])
          .map((v) => Number(v))
          .filter((v) => Number.isFinite(v));
        if (!numericValues.length) {
          return null;
        }
        const rawMin = Math.min(...numericValues);
        const rawMax = Math.max(...numericValues);
        const span = Math.max(rawMax - rawMin, minSpan);
        let min = rawMin - pad;
        let max = rawMax + pad;
        if ((max - min) < span) {
          const center = (rawMin + rawMax) / 2;
          min = center - span / 2;
          max = center + span / 2;
        }
        if (minClamp !== null) min = Math.max(min, minClamp);
        if (maxClamp !== null) max = Math.min(max, maxClamp);
        if (max <= min) {
          max = min + Math.max(minSpan, 1);
        }
        const factor = 10 ** precision;
        return {
          min: Math.floor(min * factor) / factor,
          max: Math.ceil(max * factor) / factor,
        };
      }

      function chartOrNote(id) {
        const el = document.getElementById(id);
        if (!el) return null;
        if (!window.echarts) {
          el.innerHTML = '<p class="muted-note">ECharts 未加载，无法渲染图表</p>';
          return null;
        }
        const chart = window.echarts.init(el);
        chartRefs.push(chart);
        return chart;
      }

      const overview = report.activity_overview || {};
      const health = report.health_overview || {};
      const running = ((report.sports || {}).running) || {};
      const swimming = ((report.sports || {}).swimming) || {};
      const typeAnalysis = ((report.sports || {}).type_analysis) || {};
      const monthly = report.monthly_trends || {};
      const dailyTrends = report.daily_trends || {};
      const monthlyPrev = report.previous_monthly_trends || {};
      const compareRows = Array.isArray(report.comparison_rows) ? report.comparison_rows : [];
      const compareIntensityCards = Array.isArray(report.monthly_intensity_compare_cards)
        ? report.monthly_intensity_compare_cards
        : [];
      const exportBtn = document.getElementById('btn-export-pdf');
      const reportShell = document.querySelector('.report-shell');
      const compareDetails = document.getElementById('compare-details');
      const isMobile = window.matchMedia('(max-width: 760px)').matches;
      const exportBtnDefaultText = exportBtn ? (exportBtn.textContent || '分享 / 打印 PDF') : '分享 / 打印 PDF';
      let printInProgress = false;
      const dailyCaloriesByDate = dailyTrends.calories_by_date || {};
      const dailyDurationByDate = dailyTrends.duration_h_by_date || {};
      const dailyIntensityByDate = dailyTrends.intensity_minutes_by_date || {};
      const dailyWeightByDate = dailyTrends.weight_kg_by_date || {};
      const dailyBodyAgeByDate = dailyTrends.body_age_by_date || {};
      const dailyRestingHeartRateByDate = dailyTrends.resting_heart_rate_by_date || {};
      const weeklyIntensityMinutes = report.weekly_intensity_minutes || {};
      const ISO_VIEW_MODES = ['2d', '3d', 'both'];
      const hasBodyAgeData = Object.keys(dailyBodyAgeByDate).length > 0;

      if (!hasBodyAgeData) {
        const bodyAgeChartEl = document.getElementById('chart-health-body-age-trend');
        const bodyAgePanel = bodyAgeChartEl ? bodyAgeChartEl.closest('.panel') : null;
        if (bodyAgePanel) {
          bodyAgePanel.remove();
        }
        const weightPanel = document.getElementById('chart-health-weight-trend')?.closest('.panel');
        const rhrPanel = document.getElementById('chart-health-resting-hr-trend')?.closest('.panel');
        if (weightPanel) {
          weightPanel.style.gridColumn = 'span 6';
        }
        if (rhrPanel) {
          rhrPanel.style.gridColumn = 'span 6';
        }
      }

      function resolveInitialIsoViewMode() {
        const params = new URLSearchParams(window.location.search);
        const fromQuery = (params.get('isoView') || '').toLowerCase();
        if (ISO_VIEW_MODES.includes(fromQuery)) return fromQuery;
        try {
          const saved = (localStorage.getItem('garmin-report-iso-view') || '').toLowerCase();
          if (ISO_VIEW_MODES.includes(saved)) return saved;
        } catch (err) {
          console.warn('读取热力图视图设置失败', err);
        }
        return isMobile ? '3d' : 'both';
      }

      let isoViewMode = resolveInitialIsoViewMode();

      function updateIsoViewButtons() {
        document.querySelectorAll('.iso-view-btn').forEach((btn) => {
          const mode = (btn.dataset.isoMode || '').toLowerCase();
          btn.classList.toggle('active', mode === isoViewMode);
        });
      }

      function updateIsoViewContainers() {
        ['chart-sports-daily-calories-3d', 'chart-sports-daily-duration-3d'].forEach((id) => {
          const el = document.getElementById(id);
          if (el) {
            el.setAttribute('data-iso-view-mode', isoViewMode);
            const stage = el.querySelector('.iso-stage');
            if (stage) {
              stage.setAttribute('data-iso-view-mode', isoViewMode);
            }
          }
        });
      }

      function setIsoViewMode(nextMode, persist) {
        const mode = String(nextMode || '').toLowerCase();
        if (!ISO_VIEW_MODES.includes(mode)) return;
        isoViewMode = mode;
        updateIsoViewButtons();
        updateIsoViewContainers();
        if (persist) {
          try {
            localStorage.setItem('garmin-report-iso-view', isoViewMode);
          } catch (err) {
            console.warn('保存热力图视图设置失败', err);
          }
        }
        if (typeof customResizers.sportsDailyCalories3D === 'function') {
          customResizers.sportsDailyCalories3D();
        }
        if (typeof customResizers.sportsDailyDuration3D === 'function') {
          customResizers.sportsDailyDuration3D();
        }
      }

      document.querySelectorAll('.iso-view-btn').forEach((btn) => {
        btn.addEventListener('click', function () {
          setIsoViewMode(btn.dataset.isoMode, true);
        });
      });
      updateIsoViewButtons();
      updateIsoViewContainers();

      if (compareDetails && isMobile) {
        compareDetails.open = false;
      }

      async function shareReportLink() {
        const shareTitle = `Garmin ${report.year || ''} 年度报告`;
        try {
          if (navigator.share) {
            await navigator.share({
              title: shareTitle,
              text: '我的 Garmin 年度运动报告',
              url: window.location.href,
            });
            showToast('已打开系统分享面板', 'success');
            return true;
          }
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(window.location.href);
            showToast('报告链接已复制到剪贴板', 'success');
            return true;
          }
        } catch (err) {
          console.error('分享失败', err);
          showToast('分享失败，请重试', 'error');
          return false;
        }
        showToast('当前浏览器不支持分享', 'error');
        return false;
      }

      setText('hero-total-activities', fmtNumber(overview.total_activities || 0, 0) + ' 次');
      setText('hero-total-distance', fmtNumber((overview.total_distance_m || 0) / 1000, 1) + ' km');
      setText('hero-total-duration', fmtNumber((overview.total_duration_s || 0) / 3600, 1) + ' h');

      setHtml('overview-kpis', [
        metricCard('活动总数', fmtNumber(overview.total_activities || 0, 0), '全年总活动次数'),
        metricCard('活跃天数', fmtNumber(overview.active_days || 0, 0), '有运动记录的天数'),
        metricCard('总距离', fmtNumber((overview.total_distance_m || 0) / 1000, 1) + ' km', ''),
        metricCard('总时长', fmtNumber((overview.total_duration_s || 0) / 3600, 1) + ' h', ''),
        metricCard('总卡路里', fmtNumber(overview.total_calories || 0, 0) + ' kcal', ''),
        metricCard('总爬升', fmtNumber(overview.total_elevation_gain_m || 0, 0) + ' m', ''),
      ].join(''));

      setHtml('sports-kpis', [
        metricCard('跑步次数', fmtNumber(running.count || 0, 0), ''),
        metricCard('跑步总距离', fmtNumber((running.total_distance_m || 0) / 1000, 1) + ' km', ''),
        metricCard('跑步平均配速', running.avg_pace_min_per_km ? fmtNumber(running.avg_pace_min_per_km, 2) + ' min/km' : 'N/A', ''),
        metricCard('游泳次数', fmtNumber(swimming.count || 0, 0), ''),
        metricCard('游泳总距离', fmtNumber((swimming.total_distance_m || 0) / 1000, 1) + ' km', ''),
        metricCard('游泳平均配速', swimming.avg_pace_min_per_100m ? fmtNumber(swimming.avg_pace_min_per_100m, 2) + ' min/100m' : 'N/A', ''),
      ].join(''));

      setHtml('health-kpis', [
        metricCard('睡眠记录', fmtNumber(health.sleep_recorded_days || 0, 0) + ' 天', ''),
        metricCard('平均睡眠时长', fmtNumber(health.avg_sleep_hours || 0, 2) + ' h', ''),
        metricCard('平均睡眠分数', fmtNumber(health.avg_sleep_score || 0, 1), ''),
        metricCard('平均深睡时长', fmtNumber(health.avg_deep_sleep_hours || 0, 2) + ' h', ''),
        metricCard('总步数', fmtNumber(health.total_steps || 0, 0) + ' 步', ''),
        metricCard('日均步数', fmtNumber(health.avg_daily_steps || 0, 0) + ' 步', ''),
        metricCard('日均强度活动', fmtNumber(health.avg_daily_intensity_minutes || 0, 1) + ' min', ''),
      ].join(''));

      setHtml('table-running', renderTopTable((report.tables || {}).running_top, false));
      setHtml('table-swimming', renderTopTable((report.tables || {}).swimming_top, false));
      setHtml('table-top-activities', renderTopTable((report.tables || {}).top_activities, true));

      setHtml('compare-rows', compareRows.length ? compareRows.map((row) => {
        const pctClass = (row.pct_change || 0) >= 0 ? 'pos' : 'neg';
        const unit = row.unit || '';
        return `
          <div class="compare-row">
            <div class="compare-cell section">${row.section || ''}</div>
            <div class="compare-cell label">${row.label || ''}</div>
            <div class="compare-cell">
              <span class="cell-tag">上一年</span>${fmtNumber(row.previous || 0, 2)} ${unit}
            </div>
            <div class="compare-cell">
              <span class="cell-tag">本年度</span>${fmtNumber(row.current || 0, 2)} ${unit}
            </div>
            <div class="compare-cell pct ${pctClass}">
              <span class="cell-tag">同比</span>${fmtPct(row.pct_change || 0)}
            </div>
          </div>
        `;
      }).join('') : '<p class="muted-note">分析文件中没有上一年同比字段。</p>');
      setHtml('compare-monthly-intensity-cards', renderCompareMonthlyIntensityCards(compareIntensityCards));

      const common = getChartTheme();
      const labels = monthly.labels || [];
      const typeLabels = typeAnalysis.labels || [];
      let overviewChart = null;
      let sportPie = null;
      let overviewTypeCalories = null;
      let overviewTypeDuration = null;
      let overviewTypeIntensity = null;
      let sportMatrix = null;
      let sportCalories = null;
      let sportsWeeklyIntensityGoal = null;
      let healthMonthly = null;
      let healthWeightTrend = null;
      let healthBodyAgeTrend = null;
      let healthRestingHeartRateTrend = null;
      let compareMonthly = null;

      function ensureOverviewChart() {
        if (overviewChart) return overviewChart;
        overviewChart = chartOrNote('chart-overview-monthly');
        if (!overviewChart) return null;
        overviewChart.setOption({
          ...common,
          legend: { ...common.legend, data: ['月度里程(km)', '活动次数'] },
          xAxis: { ...common.xAxis, type: 'category', data: labels },
          yAxis: [
            { ...common.yAxis, type: 'value', name: 'km' },
            { ...common.yAxis, type: 'value', name: '次' },
          ],
          series: [
            {
              name: '月度里程(km)',
              type: 'bar',
              data: monthly.distance_km || [],
              itemStyle: { color: '#4ca7ff', borderRadius: [6, 6, 0, 0] },
            },
            {
              name: '活动次数',
              type: 'line',
              yAxisIndex: 1,
              smooth: true,
              data: monthly.activity_count || [],
              lineStyle: { width: 3, color: '#54f1d2' },
              itemStyle: { color: '#54f1d2' },
            },
          ],
        });
        return overviewChart;
      }

      function ensureSportPieChart() {
        if (sportPie) return sportPie;
        sportPie = chartOrNote('chart-sport-type-pie');
        if (!sportPie) return null;
        sportPie.setOption({
          backgroundColor: 'transparent',
          tooltip: {
            trigger: 'item',
            backgroundColor: 'rgba(7, 16, 38, 0.95)',
            borderColor: 'rgba(100, 153, 255, 0.3)',
            textStyle: { color: '#f4f8ff' }
          },
          series: [
            {
              type: 'pie',
              radius: ['34%', '72%'],
              roseType: 'radius',
              itemStyle: { borderColor: '#0e1a36', borderWidth: 2 },
              label: { color: '#d7e6ff' },
              data: typeLabels.map((label, idx) => ({
                name: label,
                value: (typeAnalysis.by_count || [])[idx] || 0,
              })),
            },
          ],
        });
        return sportPie;
      }

      function setTypeDonutOption(chart, metricName, values, unitLabel) {
        chart.setOption({
          backgroundColor: 'transparent',
          tooltip: {
            trigger: 'item',
            backgroundColor: 'rgba(7, 16, 38, 0.95)',
            borderColor: 'rgba(100, 153, 255, 0.3)',
            textStyle: { color: '#f4f8ff' },
            formatter: function (params) {
              const val = Number(params.value || 0);
              return `${params.name}<br/>${metricName}: ${fmtNumber(val, 2)} ${unitLabel}`;
            },
          },
          legend: {
            show: false,
          },
          series: [
            {
              name: metricName,
              type: 'pie',
              radius: ['42%', '72%'],
              center: ['50%', '54%'],
              avoidLabelOverlap: true,
              minAngle: 4,
              label: {
                color: '#d7e6ff',
                formatter: function (params) {
                  return `${compactLabel(params.name)}\\n${params.percent.toFixed(0)}%`;
                },
                fontSize: isMobile ? 10 : 11,
              },
              itemStyle: { borderColor: '#0e1a36', borderWidth: 2 },
              data: typeLabels.map((label, idx) => ({
                name: label,
                value: (values || [])[idx] || 0,
              })),
            },
          ],
        });
      }

      function ensureOverviewTypeDistributionCharts() {
        if (!overviewTypeCalories) {
          overviewTypeCalories = chartOrNote('chart-overview-type-calories');
          if (overviewTypeCalories) {
            setTypeDonutOption(overviewTypeCalories, '卡路里', typeAnalysis.by_calories || [], 'kcal');
          }
        }
        if (!overviewTypeDuration) {
          overviewTypeDuration = chartOrNote('chart-overview-type-duration');
          if (overviewTypeDuration) {
            setTypeDonutOption(overviewTypeDuration, '时长', typeAnalysis.by_duration_h || [], 'h');
          }
        }
        if (!overviewTypeIntensity) {
          overviewTypeIntensity = chartOrNote('chart-overview-type-intensity');
          if (overviewTypeIntensity) {
            setTypeDonutOption(overviewTypeIntensity, '强度时间', typeAnalysis.by_intensity_minutes || [], 'min');
          }
        }
        if (overviewTypeCalories) overviewTypeCalories.resize();
        if (overviewTypeDuration) overviewTypeDuration.resize();
        if (overviewTypeIntensity) overviewTypeIntensity.resize();
      }

      function ensureSportMatrixChart() {
        if (sportMatrix) return sportMatrix;
        sportMatrix = chartOrNote('chart-sport-matrix');
        if (!sportMatrix) return null;
        sportMatrix.setOption({
          ...common,
          grid: isMobile ? { ...common.grid, left: 36, right: 14, bottom: 58 } : common.grid,
          legend: { ...common.legend, data: ['次数', '时长(h)', '距离(km)'] },
          xAxis: {
            ...common.xAxis,
            type: 'category',
            data: typeLabels,
            axisLabel: {
              color: '#90a8db',
              rotate: isMobile ? 24 : 0,
              interval: 0,
            },
          },
          yAxis: { ...common.yAxis, type: 'value' },
          series: [
            {
              name: '次数',
              type: 'bar',
              data: typeAnalysis.by_count || [],
              itemStyle: { color: '#5fa7ff' },
            },
            {
              name: '时长(h)',
              type: 'bar',
              data: typeAnalysis.by_duration_h || [],
              itemStyle: { color: '#4ce1d4' },
            },
            {
              name: '距离(km)',
              type: 'line',
              smooth: true,
              data: typeAnalysis.by_distance_km || [],
              lineStyle: { width: 2.8, color: '#ff9f70' },
              itemStyle: { color: '#ff9f70' },
            },
          ],
        });
        return sportMatrix;
      }

      function ensureSportCaloriesChart() {
        if (sportCalories) return sportCalories;
        sportCalories = chartOrNote('chart-sport-calories');
        if (!sportCalories) return null;
        sportCalories.setOption({
          ...common,
          grid: isMobile ? { ...common.grid, left: 36, right: 14, bottom: 66 } : common.grid,
          xAxis: {
            ...common.xAxis,
            type: 'category',
            data: typeLabels,
            axisLabel: {
              rotate: isMobile ? 35 : 20,
              color: '#90a8db',
              interval: 0,
              formatter: compactLabel,
            },
          },
          yAxis: { ...common.yAxis, type: 'value', name: 'kcal' },
          series: [
            {
              name: '卡路里',
              type: 'bar',
              data: typeAnalysis.by_calories || [],
              itemStyle: { color: '#ff7a9e', borderRadius: [6, 6, 0, 0] },
            }
          ],
        });
        return sportCalories;
      }

      function ensureSportsWeeklyIntensityGoalChart() {
        if (sportsWeeklyIntensityGoal) return sportsWeeklyIntensityGoal;
        sportsWeeklyIntensityGoal = chartOrNote('chart-sports-weekly-intensity-goal');
        if (!sportsWeeklyIntensityGoal) return null;
        const labelsData = Array.isArray(weeklyIntensityMinutes.labels) ? weeklyIntensityMinutes.labels : [];
        const actualData = Array.isArray(weeklyIntensityMinutes.actual_minutes) ? weeklyIntensityMinutes.actual_minutes : [];
        const goal = Number(weeklyIntensityMinutes.goal_minutes || 200);
        const goalData = labelsData.map(() => goal);
        sportsWeeklyIntensityGoal.setOption({
          ...common,
          grid: isMobile ? { ...common.grid, left: 32, right: 14, bottom: 68 } : { ...common.grid, left: 46, right: 20, bottom: 56 },
          legend: { ...common.legend, data: ['目标值', '实际强度分钟'] },
          xAxis: {
            ...common.xAxis,
            type: 'category',
            data: labelsData,
            axisLabel: {
              color: '#90a8db',
              interval: isMobile ? 3 : 1,
              rotate: isMobile ? 35 : 0,
            },
          },
          yAxis: { ...common.yAxis, type: 'value', name: 'min' },
          series: [
            {
              name: '目标值',
              type: 'bar',
              data: goalData,
              barWidth: isMobile ? 9 : 12,
              barGap: '-100%',
              itemStyle: { color: 'rgba(135, 152, 186, 0.36)', borderRadius: [4, 4, 0, 0] },
              z: 1,
            },
            {
              name: '实际强度分钟',
              type: 'bar',
              data: actualData,
              barWidth: isMobile ? 7 : 9,
              itemStyle: {
                borderRadius: [4, 4, 0, 0],
                color: function (params) {
                  const val = Number(params.value || 0);
                  return val >= goal ? '#39d98a' : '#5ea7ff';
                },
              },
              z: 2,
            },
          ],
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(7, 16, 38, 0.95)',
            borderColor: 'rgba(100, 153, 255, 0.3)',
            textStyle: { color: '#f4f8ff' },
            formatter: function (params) {
              const actual = Number((params || []).find((item) => item.seriesName === '实际强度分钟')?.value || 0);
              const ratio = goal > 0 ? (actual / goal) * 100 : 0;
              return `${params?.[0]?.axisValue || ''}<br/>目标值: ${fmtNumber(goal, 0)} min<br/>实际: ${fmtNumber(actual, 1)} min<br/>达成率: ${fmtNumber(ratio, 1)}%`;
            },
          },
        });
        return sportsWeeklyIntensityGoal;
      }

      function renderIsometricContributionChart(containerId, dailyMap, options) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = '';
        if (!window.obelisk) {
          container.innerHTML = '<p class="muted-note">Obelisk.js 未加载，无法渲染等距热力图</p>';
          return;
        }
        const metricLabel = options.metricLabel || '贡献';
        const unitLabel = options.unitLabel || '';
        const weekLabel = options.weekLabel || '最佳一周';
        const dayLabel = options.dayLabel || '最佳一天';
        const valuePrecision = Number.isFinite(options.valuePrecision) ? options.valuePrecision : 0;
        const tiltDegrees = clamp(Number(options.tiltDegrees || 60), 40, 72);
        const tiltFactor = Math.tan((tiltDegrees * (Math.PI / 180))) / Math.tan(45 * (Math.PI / 180));
        const palette = Array.isArray(options.palette) && options.palette.length >= 5
          ? options.palette
          : ['161b22', '0e4429', '006d32', '26a641', '39d353'];
        const contribution = buildIsoContributionData(dailyMap);
        container.setAttribute('data-iso-view-mode', isoViewMode);

        const stats = document.createElement('div');
        stats.className = 'iso-stats';
        stats.innerHTML = `
          <div style="font-size: 10px; color: #92a8d6;">${metricLabel}</div>
          <div class="big">${fmtNumber(contribution.total || 0, valuePrecision)}</div>
          <div>平均 ${fmtNumber(contribution.average || 0, 2)} / 天</div>
          <div class="row"><span>${weekLabel}</span><span>${fmtNumber(contribution.bestWeekTotal || 0, valuePrecision)} ${unitLabel}</span></div>
          <div class="row"><span>${dayLabel}</span><span>${fmtNumber(contribution.bestValue || 0, valuePrecision)} ${unitLabel}</span></div>
        `;
        container.appendChild(stats);

        const stage = document.createElement('div');
        stage.className = 'iso-stage';
        stage.setAttribute('data-iso-view-mode', isoViewMode);
        container.appendChild(stage);

        const wrap3d = document.createElement('div');
        wrap3d.className = 'iso-3d-wrap';
        stage.appendChild(wrap3d);

        const canvas = document.createElement('canvas');
        canvas.className = 'iso-canvas';
        canvas.title = `${metricLabel} 等距热力图`;
        wrap3d.appendChild(canvas);

        const wrap2d = document.createElement('div');
        wrap2d.className = 'iso-2d-wrap';
        stage.appendChild(wrap2d);
        renderFlatContributionGrid(wrap2d, contribution, { palette, unitLabel });

        if (isoViewMode === '2d') {
          return;
        }

        const rect = wrap3d.getBoundingClientRect();
        const dpr = Math.max(1, window.devicePixelRatio || 1);
        const cssWidth = Math.max(280, Math.floor(rect.width || wrap3d.clientWidth || 560));
        const cssHeight = Math.max(180, Math.floor(rect.height || wrap3d.clientHeight || 300));
        canvas.width = Math.floor(cssWidth * dpr);
        canvas.height = Math.floor(cssHeight * dpr);
        canvas.style.width = `${cssWidth}px`;
        canvas.style.height = `${cssHeight}px`;

        const weekCount = Math.max(contribution.weeks.length, 1);
        const isBothMode = isoViewMode === 'both';
        const statsWidthCss = !isMobile ? Math.ceil(stats.getBoundingClientRect().width || 0) : 0;
        const statsReservePx = !isMobile ? Math.ceil(statsWidthCss * dpr) + Math.ceil((isBothMode ? 12 : 16) * dpr) : 0;
        const padLeft = Math.ceil(12 * dpr);
        const padTop = Math.ceil((isMobile ? 8 : 14) * dpr);
        const padBottom = Math.ceil((isMobile ? 12 : 16) * dpr);
        const padRight = Math.ceil((isBothMode ? 8 : 12) * dpr) + statsReservePx;
        const availWidth = Math.max(1, canvas.width - padLeft - padRight);
        const availHeight = Math.max(1, canvas.height - padTop - padBottom);
        const effectiveWidth = Math.max(220, canvas.width - statsReservePx - Math.ceil((isBothMode ? 24 : 20) * dpr));
        const rawStep = Math.floor((effectiveWidth * (isBothMode ? 0.9 : 0.96)) / weekCount);
        const minStep = isMobile ? 6 : 8;
        const maxStep = isMobile ? 14 : 28;
        let step = clamp(rawStep, minStep, maxStep);
        const maxCubeHeight = Math.max(
          normalizeIsoCubeHeight(Math.round(canvas.height * (isBothMode ? 0.16 : 0.2))),
          isMobile ? 20 : 38
        );

        try {
          const fallbackColor = Number.parseInt(palette[0], 16);
          function buildGeometry(stepValue) {
            const cubeSize = normalizeIsoAxisSize(Math.round(stepValue * (isMobile ? 0.9 : 0.78)));
            const baseHeight = normalizeIsoCubeHeight(Math.round(cubeSize * 0.16));
            const yStep = Math.max(2, Math.round(Math.max(2, cubeSize - 2) * tiltFactor));
            const cubes = [];
            let minGX = Infinity;
            let maxGX = -Infinity;
            let minGY = Infinity;
            let maxGY = -Infinity;
            contribution.weeks.forEach((week, weekIdx) => {
              week.forEach((day, dayIdx) => {
                const x3 = stepValue * weekIdx;
                const y3 = yStep * dayIdx;
                const value = Number(day.value || 0);
                const level = valueToLevel(value, contribution.maxVal);
                const colorHex = palette[level] || palette[0];
                const cubeHeight = normalizeIsoCubeHeight(baseHeight + (
                  contribution.maxVal > 0
                    ? Math.round(maxCubeHeight * (value / contribution.maxVal))
                    : 0
                ));
                const gx = x3 - y3;
                const gy = Math.floor((x3 + y3) / 2);
                minGX = Math.min(minGX, gx - cubeSize - 3);
                maxGX = Math.max(maxGX, gx + cubeSize + 3);
                minGY = Math.min(minGY, gy - cubeHeight - cubeSize - 3);
                maxGY = Math.max(maxGY, gy + Math.ceil(cubeSize / 2) + 3);
                cubes.push({
                  x3,
                  y3,
                  cubeHeight,
                  colorValue: Number.parseInt(colorHex, 16),
                });
              });
            });
            return {
              cubes,
              cubeSize,
              minGX,
              maxGX,
              minGY,
              maxGY,
              drawWidth: Math.max(1, maxGX - minGX),
              drawHeight: Math.max(1, maxGY - minGY),
            };
          }

          let geometry = buildGeometry(step);
          while (
            step > minStep
            && (geometry.drawWidth > availWidth || geometry.drawHeight > availHeight)
          ) {
            step -= 1;
            geometry = buildGeometry(step);
          }
          if (!Number.isFinite(geometry.minGX) || !Number.isFinite(geometry.minGY)) {
            return;
          }
          const originX = padLeft + Math.max(0, Math.floor((availWidth - geometry.drawWidth) / 2)) - geometry.minGX;
          const originY = padTop + Math.max(0, Math.floor((availHeight - geometry.drawHeight) / 2)) - geometry.minGY;
          const point = new obelisk.Point(originX, originY);
          const pixelView = new obelisk.PixelView(canvas, point);

          geometry.cubes.forEach((item) => {
            const dimension = new obelisk.CubeDimension(geometry.cubeSize, geometry.cubeSize, item.cubeHeight);
            const color = new obelisk.CubeColor().getByHorizontalColor(
              Number.isFinite(item.colorValue) ? item.colorValue : fallbackColor
            );
            const cube = new obelisk.Cube(dimension, color, false);
            const p3d = new obelisk.Point3D(item.x3, item.y3, 0);
            pixelView.renderObject(cube, p3d);
          });
        } catch (err) {
          console.error('isometric contribution chart render failed', err);
          container.innerHTML = '<p class="muted-note">3D 热力图渲染失败，请刷新后重试。</p>';
        }
      }

      function ensureSports3DContributionCharts() {
        customResizers.sportsDailyCalories3D = function () {
          renderIsometricContributionChart(
            'chart-sports-daily-calories-3d',
            dailyCaloriesByDate,
            {
              metricLabel: '卡路里贡献',
              unitLabel: 'kcal',
              weekLabel: '最佳一周消耗',
              dayLabel: '最佳一天消耗',
              valuePrecision: 0,
              tiltDegrees: 60,
              palette: ['161b22', '0e4429', '006d32', '26a641', '39d353'],
            }
          );
        };
        customResizers.sportsDailyDuration3D = function () {
          renderIsometricContributionChart(
            'chart-sports-daily-duration-3d',
            dailyDurationByDate,
            {
              metricLabel: '时长贡献',
              unitLabel: 'h',
              weekLabel: '最佳一周时长',
              dayLabel: '最佳一天时长',
              valuePrecision: 2,
              tiltDegrees: 60,
              palette: ['161b22', '0a3f5d', '0b5f8a', '1f87be', '49b9ff'],
            }
          );
        };
        customResizers.sportsDailyCalories3D();
        customResizers.sportsDailyDuration3D();
      }

      function ensureHealthMonthlyChart() {
        if (healthMonthly) return healthMonthly;
        healthMonthly = chartOrNote('chart-health-monthly');
        if (!healthMonthly) return null;
        healthMonthly.setOption({
          ...common,
          legend: { ...common.legend, data: ['月度步数', '月度睡眠时长(h)'] },
          xAxis: { ...common.xAxis, type: 'category', data: labels },
          yAxis: [
            { ...common.yAxis, type: 'value', name: '步数' },
            { ...common.yAxis, type: 'value', name: 'h' },
          ],
          series: [
            {
              name: '月度步数',
              type: 'bar',
              data: monthly.steps_by_month || [],
              itemStyle: { color: '#5c86ff', borderRadius: [6, 6, 0, 0] },
            },
            {
              name: '月度睡眠时长(h)',
              type: 'line',
              yAxisIndex: 1,
              smooth: true,
              data: monthly.sleep_hours_by_month || [],
              lineStyle: { width: 3, color: '#5dffd8' },
              itemStyle: { color: '#5dffd8' },
            },
          ],
        });
        return healthMonthly;
      }

      function ensureHealthDailyTrendCharts() {
        const weightSeries = buildSortedDailySeries(dailyWeightByDate);
        const bodyAgeSeries = buildSortedDailySeries(dailyBodyAgeByDate);
        const restingHrSeries = buildSortedDailySeries(dailyRestingHeartRateByDate);
        const weightRange = computeSeriesRange(weightSeries.values, { pad: 0.25, minSpan: 1.2, precision: 1, minClamp: 0 });
        const restingHrRange = computeSeriesRange(restingHrSeries.values, { pad: 1.0, minSpan: 8.0, precision: 0, minClamp: 0 });

        if (!healthWeightTrend) {
          healthWeightTrend = chartOrNote('chart-health-weight-trend');
        }
        if (healthWeightTrend) {
          healthWeightTrend.setOption({
            ...common,
            grid: isMobile ? { ...common.grid, left: 34, right: 12, bottom: 58 } : { ...common.grid, left: 42, right: 16, bottom: 48 },
            legend: { ...common.legend, data: ['体重'] },
            xAxis: {
              ...common.xAxis,
              type: 'category',
              data: weightSeries.dates,
              axisLabel: {
                color: '#90a8db',
                interval: isMobile ? 29 : 'auto',
                formatter: (value) => String(value || '').slice(5),
              },
            },
            yAxis: {
              ...common.yAxis,
              type: 'value',
              name: 'kg',
              min: weightRange ? weightRange.min : null,
              max: weightRange ? weightRange.max : null,
              scale: true,
            },
            series: [
              {
                name: '体重',
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 4,
                data: weightSeries.values,
                lineStyle: { width: 2.8, color: '#6bc6ff' },
                itemStyle: { color: '#6bc6ff' },
                areaStyle: { color: 'rgba(107, 198, 255, 0.16)' },
                markPoint: {
                  symbolSize: 34,
                  label: { color: '#e9f4ff', fontSize: 10 },
                  data: [{ type: 'max', name: '最高' }, { type: 'min', name: '最低' }],
                },
              },
            ],
          });
        }

        if (!healthBodyAgeTrend) {
          healthBodyAgeTrend = chartOrNote('chart-health-body-age-trend');
        }
        if (healthBodyAgeTrend) {
          healthBodyAgeTrend.setOption({
            ...common,
            grid: isMobile ? { ...common.grid, left: 34, right: 12, bottom: 58 } : { ...common.grid, left: 42, right: 16, bottom: 48 },
            legend: { ...common.legend, data: ['身体年龄'] },
            xAxis: {
              ...common.xAxis,
              type: 'category',
              data: bodyAgeSeries.dates,
              axisLabel: {
                color: '#90a8db',
                interval: isMobile ? 29 : 'auto',
                formatter: (value) => String(value || '').slice(5),
              },
            },
            yAxis: { ...common.yAxis, type: 'value', name: '岁' },
            series: [
              {
                name: '身体年龄',
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 4,
                data: bodyAgeSeries.values,
                lineStyle: { width: 2.8, color: '#8de39d' },
                itemStyle: { color: '#8de39d' },
                areaStyle: { color: 'rgba(141, 227, 157, 0.14)' },
              },
            ],
          });
        }

        if (!healthRestingHeartRateTrend) {
          healthRestingHeartRateTrend = chartOrNote('chart-health-resting-hr-trend');
        }
        if (healthRestingHeartRateTrend) {
          healthRestingHeartRateTrend.setOption({
            ...common,
            grid: isMobile ? { ...common.grid, left: 34, right: 12, bottom: 58 } : { ...common.grid, left: 42, right: 16, bottom: 48 },
            legend: { ...common.legend, data: ['静息心率'] },
            xAxis: {
              ...common.xAxis,
              type: 'category',
              data: restingHrSeries.dates,
              axisLabel: {
                color: '#90a8db',
                interval: isMobile ? 29 : 'auto',
                formatter: (value) => String(value || '').slice(5),
              },
            },
            yAxis: {
              ...common.yAxis,
              type: 'value',
              name: 'bpm',
              min: restingHrRange ? restingHrRange.min : null,
              max: restingHrRange ? restingHrRange.max : null,
              scale: true,
            },
            series: [
              {
                name: '静息心率',
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 4,
                data: restingHrSeries.values,
                lineStyle: { width: 2.8, color: '#ff9ab4' },
                itemStyle: { color: '#ff9ab4' },
                areaStyle: { color: 'rgba(255, 154, 180, 0.15)' },
                markPoint: {
                  symbolSize: 34,
                  label: { color: '#ffe8ef', fontSize: 10 },
                  data: [{ type: 'max', name: '最高' }, { type: 'min', name: '最低' }],
                },
              },
            ],
          });
        }

        if (healthWeightTrend) healthWeightTrend.resize();
        if (healthBodyAgeTrend) healthBodyAgeTrend.resize();
        if (healthRestingHeartRateTrend) healthRestingHeartRateTrend.resize();
      }

      function ensureCompareMonthlyChart() {
        if (compareMonthly) return compareMonthly;
        compareMonthly = chartOrNote('chart-compare-monthly');
        if (!compareMonthly) return null;
        compareMonthly.setOption({
          ...common,
          legend: { ...common.legend, data: [String(report.previous_year || ''), String(report.year || '')] },
          xAxis: { ...common.xAxis, type: 'category', data: labels },
          yAxis: { ...common.yAxis, type: 'value', name: 'km' },
          series: [
            {
              name: String(report.previous_year || ''),
              type: 'line',
              smooth: true,
              data: monthlyPrev.distance_km || [],
              lineStyle: { width: 2.5, color: '#8da4cf' },
              itemStyle: { color: '#8da4cf' },
              areaStyle: { color: 'rgba(141, 164, 207, 0.18)' },
            },
            {
              name: String(report.year || ''),
              type: 'line',
              smooth: true,
              data: monthly.distance_km || [],
              lineStyle: { width: 3.2, color: '#59b7ff' },
              itemStyle: { color: '#59b7ff' },
              areaStyle: { color: 'rgba(89, 183, 255, 0.2)' },
            },
          ],
        });
        return compareMonthly;
      }

      function ensureTabCharts(tab) {
        if (tab === 'overview') {
          const a = ensureOverviewChart();
          const b = ensureSportPieChart();
          ensureOverviewTypeDistributionCharts();
          if (a) a.resize();
          if (b) b.resize();
          return;
        }
        if (tab === 'sports') {
          const a = ensureSportMatrixChart();
          const b = ensureSportCaloriesChart();
          const c = ensureSportsWeeklyIntensityGoalChart();
          ensureSports3DContributionCharts();
          if (a) a.resize();
          if (b) b.resize();
          if (c) c.resize();
          return;
        }
        if (tab === 'health') {
          const a = ensureHealthMonthlyChart();
          ensureHealthDailyTrendCharts();
          if (a) a.resize();
          return;
        }
        if (tab === 'compare') {
          const chart = ensureCompareMonthlyChart();
          if (chart) chart.resize();
        }
      }

      function ensureAllCharts() {
        ensureTabCharts('overview');
        ensureTabCharts('sports');
        ensureTabCharts('health');
        ensureTabCharts('compare');
      }

      function enterPrintMode() {
        if (!reportShell) return;
        reportShell.classList.add('exporting');
        ensureAllCharts();
        setTimeout(resizeAllCharts, 80);
      }

      function leavePrintMode() {
        if (!reportShell) return;
        reportShell.classList.remove('exporting');
        scheduleResizeAllCharts();
      }

      function finishPrintFlow(showTip) {
        leavePrintMode();
        if (exportBtn) {
          exportBtn.disabled = false;
          exportBtn.textContent = exportBtnDefaultText;
        }
        if (printInProgress && showTip) {
          showToast('请在打印面板中选择“另存为 PDF”', 'success');
        }
        printInProgress = false;
      }

      async function exportPdf() {
        if (!exportBtn || !reportShell) return;
        printInProgress = true;
        exportBtn.disabled = true;
        exportBtn.textContent = '打开打印面板...';
        enterPrintMode();
        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        await new Promise((resolve) => setTimeout(resolve, 220));
        try {
          window.print();
        } catch (err) {
          console.error('打开打印面板失败', err);
          showToast('无法打开打印面板', 'error');
          finishPrintFlow(false);
          return;
        }
        // Fallback for browsers that do not fire afterprint reliably.
        setTimeout(() => {
          if (printInProgress) {
            finishPrintFlow(true);
          }
        }, 8000);
      }

      if (exportBtn) {
        exportBtn.addEventListener('click', function (event) {
          if (event.shiftKey) {
            shareReportLink();
            return;
          }
          exportPdf();
        });
        exportBtn.addEventListener('contextmenu', function (event) {
          event.preventDefault();
          shareReportLink();
        });
      }

      window.addEventListener('beforeprint', function () {
        enterPrintMode();
      });
      window.addEventListener('afterprint', function () {
        finishPrintFlow(true);
      });

      function resizeAllCharts() {
        chartRefs.forEach((chart) => chart.resize());
        Object.values(customResizers).forEach((fn) => {
          if (typeof fn === 'function') {
            fn();
          }
        });
      }

      function scheduleResizeAllCharts() {
        if (resizeRaf) {
          cancelAnimationFrame(resizeRaf);
        }
        resizeRaf = requestAnimationFrame(() => {
          resizeAllCharts();
        });
      }

      function resolveActiveTab() {
        const params = new URLSearchParams(window.location.search);
        const fromQuery = params.get('tab');
        if (fromQuery && ['overview', 'sports', 'health', 'compare'].includes(fromQuery)) {
          return fromQuery;
        }
        const activeBtn = document.querySelector('.tab-button.active');
        const activeLabel = activeBtn ? (activeBtn.textContent || '').trim() : '';
        if (activeLabel === '概览总览') return 'overview';
        if (activeLabel === '运动分析') return 'sports';
        if (activeLabel === '健康洞察') return 'health';
        if (activeLabel === '年度对比') return 'compare';
        return 'overview';
      }

      window.addEventListener('resize', scheduleResizeAllCharts);
      window.addEventListener('orientationchange', scheduleResizeAllCharts);
      window.addEventListener('garmin-tab-change', function () {
        ensureTabCharts(resolveActiveTab());
        setTimeout(scheduleResizeAllCharts, 80);
      });
      ensureTabCharts(resolveActiveTab());
      setTimeout(scheduleResizeAllCharts, 50);
      const params = new URLSearchParams(window.location.search);
      if (params.get('printPreview') === '1') {
        enterPrintMode();
        setTimeout(scheduleResizeAllCharts, 120);
      }
    })();
