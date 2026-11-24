import { useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Check, Copy, FlaskConical } from 'lucide-react';
import { meetsFps, usePoll } from '../lib/api';
import { useI18n } from '../lib/i18n';
import { useLive } from '../lib/live';
import { Card, EmptyState, PageHeader, Skeleton } from '../components/ui';
import { ChartTip, Legend, useAxis } from '../components/charts';

const COMMANDS = [
  'python evaluation/run_events.py --clips data/event_clips --weights backend/weights/best.pt \\\n    --out evaluation/out/timelogic.csv',
  'python evaluation/run_events.py --clips data/event_clips --weights backend/weights/best.pt \\\n    --out evaluation/out/raw.csv --raw',
  'python evaluation/score_events.py evaluation/ground_truth/events.csv evaluation/out/durations.csv \\\n    evaluation/out/timelogic.csv evaluation/out/raw.csv --json evaluation/results.json',
];

// goal checks: same targets as evaluation/README.md
const GOALS = [
  { key: 'caught', field: 'caught_pct', pass: (v) => v >= 80, unit: '%' },
  { key: 'false', field: 'false_per_5min', pass: (v) => v < 1 },
  { key: 'delay', field: 'mean_delay_s', pass: (v) => v < 5, unit: 's' },
];

export default function EvaluationPage() {
  const { t, num, dateTime } = useI18n();
  const { data, loading } = usePoll('/evaluation/results');
  const { fps } = useLive();
  const runs = data?.runs || [];
  // the time-logic run is the system's real score; fall back to the first run
  const main = runs.find((r) => /time/i.test(r.name)) || runs[0];

  return (
    <>
      <PageHeader title={t('eval.title')} subtitle={t('eval.subtitle')} />

      <div className="grid kpis">
        {GOALS.map((g) => {
          const v = main?.[g.field];
          return <Goal key={g.key} label={t(`eval.${g.key}`)} target={t(`eval.goal.${g.key}`)}
            value={v == null ? '–' : `${num(v)}${g.unit || ''}`}
            status={v == null ? 'pending' : g.pass(v) ? 'met' : 'notMet'} />;
        })}
        <Goal label={t('eval.fps')} target={t('eval.goal.fps')} value={fps ? num(fps) : '–'}
          status={fps ? (meetsFps(fps) ? 'met' : 'notMet') : 'pending'} note={fps ? t('eval.liveNow') : null} />
      </div>

      {loading && !data ? (
        <div style={{ marginTop: 16 }}><Skeleton h={260} /></div>
      ) : runs.length === 0 ? (
        <Card>
          <EmptyState icon={FlaskConical} title={t('eval.noRuns')} hint={t('eval.noRunsHint')}>
            <div className="cmd-list">
              {COMMANDS.map((c, i) => <Cmd key={i} text={c} />)}
            </div>
          </EmptyState>
        </Card>
      ) : (
        <>
          <p className="faint small" style={{ margin: '12px 2px 0' }}>
            {t('eval.generated', { when: data.generated_at ? dateTime(data.generated_at) : '–', min: num(data.minutes), clips: num(data.clips) })}
          </p>
          <Compare runs={runs} />
          <Card title={t('eval.runs')} pad={false}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t('eval.col.run')}</th>
                    <th className="num">{t('eval.caught')}</th>
                    <th className="num">{t('eval.false')}</th>
                    <th className="num">{t('eval.delay')}</th>
                    <th className="num">{t('eval.col.alerts')}</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.name}>
                      <td className="mono">{r.name}</td>
                      <td className="num">{num(r.caught)}/{num(r.gt_events)} · {num(r.caught_pct)}%</td>
                      <td className="num">{num(r.false_per_5min)}</td>
                      <td className="num">{r.mean_delay_s == null ? '–' : `${num(r.mean_delay_s)} s`}</td>
                      <td className="num">{num(r.alerts)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </>
  );
}

function Goal({ label, target, value, status, note }) {
  const { t } = useI18n();
  const badge = { met: 'badge-ok', notMet: 'badge-bad', pending: 'badge-muted' }[status];
  return (
    <div className="kpi goal">
      <div className="kpi-label" style={{ justifyContent: 'space-between' }}>
        {label}
        <span className={`badge ${badge}`}>{t(`eval.${status}`)}</span>
      </div>
      <div className="kpi-value">{value}</div>
      <div className="goal-target">{t('eval.goals')}: {target}{note ? ` · ${note}` : ''}</div>
    </div>
  );
}

function Compare({ runs }) {
  const { t, num } = useI18n();
  const ax = useAxis();
  const palette = [ax.tk.brand, ax.tk.text3, ax.tk.hairnet, ax.tk.gloves];
  const metrics = [
    { key: 'caught_pct', label: `${t('eval.caught')} (%)` },
    { key: 'false_per_5min', label: t('eval.false') },
    { key: 'mean_delay_s', label: `${t('eval.delay')} (s)` },
  ];
  return (
    <div className="grid cols-3" style={{ marginTop: 12 }}>
      {metrics.map((m) => (
        <Card key={m.key} title={m.label} subtitle={m.key === 'caught_pct' ? t('eval.compareHint') : null}
          action={m.key === 'caught_pct' ? <Legend items={runs.map((r, i) => ({ label: r.name, color: palette[i % palette.length] }))} /> : null}>
          <div className="chart chart-sm">
            <ResponsiveContainer>
              <BarChart data={runs} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
                <CartesianGrid {...ax.grid} />
                <XAxis dataKey="name" {...ax.x} />
                <YAxis {...ax.y} allowDecimals />
                <Tooltip cursor={ax.cursor} content={<ChartTip valueFormat={num} />} />
                <Bar dataKey={m.key} name={m.label} radius={[4, 4, 0, 0]} maxBarSize={48}
                  shape={(p) => <rect x={p.x} y={p.y} width={p.width} height={Math.max(0, p.height)} rx={4}
                    fill={palette[p.index % palette.length]} />} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      ))}
    </div>
  );
}

function Cmd({ text }) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text.replace(/\\\n\s+/g, ''));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked */
    }
  };
  return (
    <div className="cmd">
      <pre>{text}</pre>
      <button className="btn" onClick={copy}>
        {copied ? <Check size={13} /> : <Copy size={13} />}{copied ? t('eval.copied') : t('eval.copy')}
      </button>
    </div>
  );
}
