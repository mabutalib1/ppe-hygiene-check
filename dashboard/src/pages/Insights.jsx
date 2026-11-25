import { useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { BellRing, ChartColumn, CircleAlert, Clock, Target } from 'lucide-react';
import { ITEMS, usePoll } from '../lib/api';
import { useI18n } from '../lib/i18n';
import { useLive } from '../lib/live';
import { Card, EmptyState, ItemTag, Kpi, PageHeader, Segmented, Skeleton } from '../components/ui';
import { BarList, ChartTip, Legend, useAxis } from '../components/charts';
import { OfflineBanner } from './Live';

export default function InsightsPage() {
  const { t, num, pct, duration, day, dateTime } = useI18n();
  const { conn } = useLive();
  const [range, setRange] = useState('7');
  const { data, loading } = usePoll(`/stats?days=${range}`, 15000);
  const ax = useAxis();
  const color = (i) => ax.tk[i];

  if (loading && !data) {
    return (
      <>
        <PageHeader title={t('insights.title')} subtitle={t('insights.subtitle')} />
        <Skeleton h={110} /><div style={{ height: 16 }} /><Skeleton h={300} />
      </>
    );
  }

  const s = data || { total: 0, open: 0, by_item: {}, by_change: {}, by_hour: [], by_day: [], fix_by_item: {}, session: { compliance: {} } };
  const top = Object.entries(s.by_item).sort((a, b) => b[1] - a[1])[0];
  const empty = !s.total;
  // "last N days" reaches back into an (N+1)th calendar day
  const days = fillDays(s.by_day, Number(range) + 1);

  return (
    <>
      {conn === 'offline' && <OfflineBanner />}
      <PageHeader title={t('insights.title')} subtitle={t('insights.subtitle')} actions={
        <Segmented value={range} onChange={setRange} label={t('alerts.range')}
          options={['1', '7', '30'].map((v) => ({ value: v, label: t(`range.${v}`) }))} />
      } />

      <div className="grid kpis">
        <Kpi icon={BellRing} label={t('insights.total')} value={num(s.total)}
          sub={empty ? null : t('insights.removedVsMissing', { removed: num(s.by_change.removed || 0), missing: num(s.by_change.missing || 0) })} />
        <Kpi icon={CircleAlert} label={t('insights.open')} value={num(s.open)} tone={s.open ? 'bad' : undefined} />
        <Kpi icon={Clock} label={t('insights.meanFix')} value={duration(s.mean_fix_s)} />
        <Kpi icon={Target} label={t('insights.topItem')} value={top ? t(`item.${top[0]}`) : '–'}
          sub={top ? `${num(top[1])} · ${pct((100 * top[1]) / s.total)}` : null} />
      </div>

      {empty ? (
        <Card>
          <EmptyState icon={ChartColumn} title={t('insights.noData')} hint={t('insights.noDataHint')} />
        </Card>
      ) : (
        <div className="grid cols-2">
          <Card title={t('insights.byDay')} action={<Legend items={ITEMS.map((i) => ({ label: t(`item.${i}`), color: color(i) }))} />}>
            <div className="chart">
              <ResponsiveContainer>
                <BarChart data={days} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
                  <CartesianGrid {...ax.grid} />
                  <XAxis dataKey="day" {...ax.x} tickFormatter={day} minTickGap={12} />
                  <YAxis {...ax.y} />
                  <Tooltip cursor={ax.cursor} content={<ChartTip labelFormat={day} />} />
                  {ITEMS.map((i, n) => (
                    <Bar key={i} dataKey={i} name={t(`item.${i}`)} stackId="a" fill={color(i)}
                      radius={n === ITEMS.length - 1 ? [4, 4, 0, 0] : 0} maxBarSize={36} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card title={t('insights.byHour')}>
            <div className="chart">
              <ResponsiveContainer>
                <BarChart data={s.by_hour} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
                  <CartesianGrid {...ax.grid} />
                  <XAxis dataKey="hour" {...ax.x} tickFormatter={(h) => `${String(h).padStart(2, '0')}`} interval={2} />
                  <YAxis {...ax.y} />
                  <Tooltip cursor={ax.cursor}
                    content={<ChartTip labelFormat={(h) => `${String(h).padStart(2, '0')}:00–${String(h).padStart(2, '0')}:59`} />} />
                  <Bar dataKey="count" name={t('insights.total')} fill={ax.tk.brand} radius={[4, 4, 0, 0]} maxBarSize={22} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card title={t('insights.byItem')}>
            <BarList rows={ITEMS.map((i) => ({
              key: i,
              label: <ItemTag item={i} />,
              value: s.by_item[i] || 0,
              color: color(i),
              sub: s.fix_by_item[i] != null ? t('insights.fixAvg', { d: duration(s.fix_by_item[i]) }) : null,
            }))} format={num} />
          </Card>

          <Compliance session={s.session} color={color} t={t} pct={pct} dateTime={dateTime} />
        </div>
      )}
      {empty && (
        <div className="grid cols-2">
          <Compliance session={s.session} color={color} t={t} pct={pct} dateTime={dateTime} />
        </div>
      )}
    </>
  );
}

function Compliance({ session, t, pct, dateTime }) {
  const rows = ITEMS.map((i) => {
    const c = session?.compliance?.[i] || { ok: 0, violation: 0, unknown: 0 };
    const known = c.ok + c.violation;
    const all = known + c.unknown;
    return {
      key: i,
      label: <ItemTag item={i} />,
      value: known ? (100 * c.ok) / known : null,
      color: 'var(--ok)',
      sub: all ? t('insights.notSeen', { pct: pct((100 * c.unknown) / all) }) : null,
    };
  });
  return (
    <Card title={t('insights.compliance')}
      subtitle={t('insights.complianceHint', { since: session?.started ? dateTime(session.started) : '–' })}>
      <BarList rows={rows} max={100} format={pct} />
    </Card>
  );
}

/** Make sure every day in the range has a bar (zero days included). */
function fillDays(byDay, n) {
  const map = Object.fromEntries(byDay.map((d) => [d.day, d]));
  const out = [];
  const today = new Date();
  for (let k = n - 1; k >= 0; k -= 1) {
    const d = new Date(today);
    d.setDate(today.getDate() - k);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    out.push({ mask: 0, gloves: 0, ...map[key], day: key });
  }
  return out;
}
