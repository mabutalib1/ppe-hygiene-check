import { useI18n } from '../lib/i18n';
import { useChartTokens } from './ui';

/** Shared axis/grid props so every chart looks the same and mirrors in Arabic. */
export function useAxis() {
  const tk = useChartTokens();
  const { lang } = useI18n();
  const rtl = lang === 'ar';
  const tick = { fill: tk.text3, fontSize: 11.5 };
  return {
    rtl,
    tk,
    grid: { stroke: tk.border, strokeDasharray: '0', vertical: false },
    x: { tick, tickLine: false, axisLine: { stroke: tk.border }, reversed: rtl, tickMargin: 6 },
    y: { tick, tickLine: false, axisLine: false, orientation: rtl ? 'right' : 'left', width: 36, allowDecimals: false },
    cursor: { fill: tk.border, fillOpacity: 0.35 },
  };
}

export function ChartTip({ active, payload, label, labelFormat, valueFormat }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tip">
      <div className="chart-tip-title">{labelFormat ? labelFormat(label) : label}</div>
      {payload.map((p) => (
        <div className="chart-tip-row" key={p.dataKey}>
          <span className="swatch" style={{ background: p.color || p.fill }} />
          {p.name}
          <b>{valueFormat ? valueFormat(p.value) : p.value}</b>
        </div>
      ))}
    </div>
  );
}

export function Legend({ items }) {
  return (
    <div className="legend">
      {items.map((i) => (
        <span key={i.label}><span className="swatch" style={{ background: i.color }} />{i.label}</span>
      ))}
    </div>
  );
}

/** Horizontal bar list: simpler and more readable than a chart for 3–7 categories. */
export function BarList({ rows, max, format }) {
  const top = max ?? Math.max(1, ...rows.map((r) => r.value || 0));
  return (
    <div className="bars">
      {rows.map((r) => (
        <div className="bar-row" key={r.key}>
          <div>{r.label}</div>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${Math.max(0, Math.min(100, (100 * (r.value || 0)) / top))}%`, background: r.color }} />
          </div>
          <div className="bar-value">{format ? format(r.value) : r.value}</div>
          {r.sub && <div className="bar-sub">{r.sub}</div>}
        </div>
      ))}
    </div>
  );
}
