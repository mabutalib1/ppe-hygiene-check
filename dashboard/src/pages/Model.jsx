import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Brain, Cpu, Crosshair, Film, Gauge, Target } from 'lucide-react';
import { CLASSES, usePoll } from '../lib/api';
import { useI18n } from '../lib/i18n';
import { Card, EmptyState, Kpi, PageHeader, Skeleton } from '../components/ui';
import { BarList, ChartTip, Legend, useAxis } from '../components/charts';

const WEAK = 0.5; // per-class mAP50 below this = label more of it
const classColor = (c, tk) => (c === 'person' ? tk.brand : tk[c.replace('no_', '')]);

export default function ModelPage() {
  const { t } = useI18n();
  const training = usePoll('/training/results');
  const config = usePoll('/config');
  const dataset = usePoll('/dataset/summary');
  const runs = training.data?.runs || [];

  return (
    <>
      <PageHeader title={t('model.title')} subtitle={t('model.subtitle')} />
      <div className="grid cols-3">
        <Running config={config.data} />
        <Card title={t('model.classes')}>
          <div className="chips">
            {CLASSES.map((c) => <span key={c} className={`chip ${c.startsWith('no_') ? 'neg' : ''}`}>{c}</span>)}
          </div>
        </Card>
        <Dataset data={dataset.data} />
      </div>

      {training.loading && !training.data ? (
        <div style={{ marginTop: 16 }}><Skeleton h={260} /></div>
      ) : runs.length === 0 ? (
        <Card>
          <EmptyState icon={Brain} title={t('model.noRuns')} hint={t('model.noRunsHint')}>
            <ol className="steps">
              {[1, 2, 3, 4].map((n) => <li key={n}><Code text={t(`model.step${n}`)} /></li>)}
            </ol>
          </EmptyState>
        </Card>
      ) : (
        <Runs runs={runs} />
      )}
    </>
  );
}

/** Render paths like training/train.py as <code>. */
function Code({ text }) {
  return (
    <span>
      {text.split(/(\S+\/\S+)/).map((part, i) => (/\S+\/\S+/.test(part) ? <code key={i}>{part}</code> : part))}
    </span>
  );
}

function Running({ config }) {
  const { t, num } = useI18n();
  const m = config?.model;
  return (
    <Card title={t('model.running')} action={m && (
      <span className={`badge ${m.detector === 'fake' ? 'badge-warn' : 'badge-ok'}`}>
        {m.detector === 'fake' ? t('model.fake') : t('model.yolo')}
      </span>
    )}>
      {!m ? <Skeleton h={90} /> : (
        <dl className="kv">
          <dt>{t('model.detector')}</dt><dd>{m.detector === 'fake' ? t('model.fake') : t('model.yolo')}</dd>
          <dt>{t('model.weights')}</dt><dd className="mono">{m.detector === 'fake' ? '–' : m.weights}</dd>
          <dt>{t('model.imgsz')}</dt><dd className="num">{num(m.imgsz)}</dd>
          <dt>{t('model.device')}</dt><dd>{m.device}</dd>
        </dl>
      )}
    </Card>
  );
}

function Dataset({ data }) {
  const { t, num } = useI18n();
  const tk = useAxis().tk;
  if (!data) return <Card title={t('model.dataset')}><Skeleton h={90} /></Card>;
  const split = Object.entries(data.by_split);
  return (
    <Card title={t('model.dataset')} subtitle={t('model.datasetHint')}
      action={<span className="badge badge-brand"><Film size={13} />{num(data.clips)} {t('model.clips')}</span>}>
      {data.clips === 0 ? <p className="muted">–</p> : (
        <>
          <div className="filter-label" style={{ marginBottom: 8 }}>{t('model.bySplit')}</div>
          <BarList rows={split.map(([k, v]) => ({ key: k, label: <span className="mono small">{k}</span>, value: v, color: tk.brand }))} format={num} />
          <div className="filter-label" style={{ margin: '14px 0 8px' }}>{t('model.byType')}</div>
          <div className="chips">
            {Object.entries(data.by_type).map(([k, v]) => <span key={k} className="chip">{k} · {num(v)}</span>)}
          </div>
        </>
      )}
    </Card>
  );
}

function Runs({ runs }) {
  const { t, num, fixed } = useI18n();
  const ax = useAxis();
  const last = runs[runs.length - 1];
  const prev = runs[runs.length - 2];
  const fmt = (v) => fixed(v, 2);
  const delta = (k) => {
    if (!prev || last[k] == null || prev[k] == null) return null;
    const d = last[k] - prev[k];
    return <span className={d >= 0 ? 'delta-up' : 'delta-down'}>{t('model.vsPrev', { d: `${d >= 0 ? '+' : '−'}${fmt(Math.abs(d))}` })}</span>;
  };
  const perClass = CLASSES.map((c) => ({ cls: c, value: last.per_class?.[c] ?? null }));
  const progress = runs.map((r, i) => ({ name: `${i + 1}. ${r.dataset}`, map50: r.map50, map50_95: r.map50_95 }));

  return (
    <>
      <div className="grid kpis" style={{ marginTop: 16 }}>
        <Kpi icon={Target} label={t('model.map50')} value={fmt(last.map50)} sub={delta('map50')} />
        <Kpi icon={Crosshair} label={t('model.map5095')} value={fmt(last.map50_95)} sub={delta('map50_95')} />
        <Kpi icon={Gauge} label={t('model.precision')} value={fmt(last.precision)} sub={delta('precision')} />
        <Kpi icon={Cpu} label={t('model.recall')} value={fmt(last.recall)} sub={delta('recall')} />
      </div>

      <div className="grid cols-2">
        <Card title={t('model.perClass')} subtitle={`${t('model.latest')}: ${last.run || last.dataset}`}
          action={<Legend items={[{ label: t('model.weak'), color: ax.tk.bad }]} />}>
          <div className="chart">
            <ResponsiveContainer>
              <BarChart data={perClass} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
                <CartesianGrid {...ax.grid} />
                <XAxis dataKey="cls" {...ax.x} interval={0} tick={{ ...ax.x.tick, fontSize: 10.5 }} />
                <YAxis {...ax.y} domain={[0, 1]} allowDecimals />
                <ReferenceLine y={WEAK} stroke={ax.tk.bad} strokeDasharray="4 4" />
                <Tooltip cursor={ax.cursor} content={<ChartTip valueFormat={fmt} />} />
                <Bar dataKey="value" name="mAP50" radius={[4, 4, 0, 0]} maxBarSize={34}>
                  {perClass.map((d) => (
                    <Cell key={d.cls} fill={d.value != null && d.value < WEAK ? ax.tk.bad : classColor(d.cls, ax.tk)}
                      fillOpacity={d.cls.startsWith('no_') ? 0.65 : 1} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title={t('model.progress')}
          action={<Legend items={[{ label: 'mAP50', color: ax.tk.brand }, { label: 'mAP50-95', color: ax.tk.text3 }]} />}>
          <div className="chart">
            <ResponsiveContainer>
              <LineChart data={progress} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
                <CartesianGrid {...ax.grid} />
                <XAxis dataKey="name" {...ax.x} />
                <YAxis {...ax.y} domain={[0, 1]} allowDecimals />
                <Tooltip content={<ChartTip valueFormat={fmt} />} />
                <Line dataKey="map50" name="mAP50" stroke={ax.tk.brand} strokeWidth={2.2} dot={{ r: 3.5 }} />
                <Line dataKey="map50_95" name="mAP50-95" stroke={ax.tk.text3} strokeWidth={2} dot={{ r: 3 }} strokeDasharray="5 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card title={t('model.runs')} pad={false}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t('model.col.date')}</th>
                <th>{t('model.col.dataset')}</th>
                <th>{t('model.col.model')}</th>
                <th className="num">{t('model.imgsz')}</th>
                <th className="num">mAP50</th>
                <th className="num">mAP50-95</th>
                {CLASSES.map((c) => <th key={c} className="num mono">{c}</th>)}
                <th>{t('model.col.note')}</th>
              </tr>
            </thead>
            <tbody>
              {[...runs].reverse().map((r, i) => (
                <tr key={`${r.run}-${i}`}>
                  <td className="num" style={{ whiteSpace: 'nowrap' }}>{r.date}</td>
                  <td>{r.dataset}</td>
                  <td className="mono">{r.model}</td>
                  <td className="num">{num(r.imgsz)}</td>
                  <td className="num"><strong>{fmt(r.map50)}</strong></td>
                  <td className="num">{fmt(r.map50_95)}</td>
                  {CLASSES.map((c) => {
                    const v = r.per_class?.[c];
                    return <td key={c} className="num" style={v != null && v < WEAK ? { color: 'var(--bad)' } : null}>{fmt(v)}</td>;
                  })}
                  <td className="muted">{r.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
