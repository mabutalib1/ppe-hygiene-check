import { useState } from 'react';
import { BellOff, Download } from 'lucide-react';
import { ITEMS, url, usePoll } from '../lib/api';
import { useI18n } from '../lib/i18n';
import { useLive } from '../lib/live';
import { Card, EmptyState, ItemTag, Lightbox, PageHeader, Segmented, Skeleton } from '../components/ui';
import { OfflineBanner } from './Live';

export default function AlertsPage() {
  const { t, num, dateTime, duration } = useI18n();
  const { conn, feed } = useLive();
  const [item, setItem] = useState('');
  const [status, setStatus] = useState('');
  const [range, setRange] = useState('7');
  const [zoom, setZoom] = useState(null);

  const q = new URLSearchParams({ limit: '500' });
  if (item) q.set('item', item);
  if (status) q.set('status', status);
  if (range !== 'all') q.set('days', range);
  // re-fetch whenever a new live event arrives, plus a slow safety poll
  const latest = feed[0] ? `${feed[0].event_id}${feed[0].ended_at || ''}` : '';
  const { data, loading } = usePoll(`/events?${q}&_=${latest}`, 20000);
  const rows = data || [];

  const exportCsv = () => {
    const head = ['event_id', 'time', 'person_id', 'item', 'change', 'ended_at', 'duration_s', 'camera'];
    const esc = (v) => (v == null ? '' : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
    const csv = [head.join(','), ...rows.map((r) => head.map((h) => esc(r[h])).join(','))].join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = `shayyek-alerts-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <>
      {conn === 'offline' && <OfflineBanner />}
      <PageHeader title={t('alerts.title')} subtitle={t('alerts.subtitle')} actions={
        <button className="btn" onClick={exportCsv} disabled={!rows.length}>
          <Download size={15} />{t('alerts.export')}
        </button>
      } />

      <Card>
        <div className="filters">
          <div className="filter">
            <span className="filter-label">{t('alerts.range')}</span>
            <Segmented value={range} onChange={setRange} label={t('alerts.range')}
              options={['1', '7', '30', 'all'].map((v) => ({ value: v, label: t(`range.${v}`) }))} />
          </div>
          <div className="filter">
            <span className="filter-label">{t('alerts.item')}</span>
            <Segmented value={item} onChange={setItem} label={t('alerts.item')}
              options={[{ value: '', label: t('all') }, ...ITEMS.map((i) => ({ value: i, label: t(`item.${i}`) }))]} />
          </div>
          <div className="filter">
            <span className="filter-label">{t('alerts.status')}</span>
            <Segmented value={status} onChange={setStatus} label={t('alerts.status')}
              options={[{ value: '', label: t('all') }, { value: 'open', label: t('alerts.open') },
                { value: 'resolved', label: t('alerts.resolved') }]} />
          </div>
          <span className="faint small" style={{ marginInlineStart: 'auto' }}>
            {t('alerts.count', { n: num(rows.length) })}
          </span>
        </div>
      </Card>

      <Card pad={false}>
        {loading && !data ? (
          <div className="card-body"><Skeleton h={240} /></div>
        ) : rows.length === 0 ? (
          <EmptyState icon={BellOff} title={t('alerts.none')} hint={t('alerts.noneHint')} />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t('alerts.col.snapshot')}</th>
                  <th>{t('alerts.col.time')}</th>
                  <th>{t('alerts.col.person')}</th>
                  <th>{t('alerts.col.item')}</th>
                  <th>{t('alerts.col.what')}</th>
                  <th>{t('alerts.col.status')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const caption = `${t('person', { id: r.person_id })} · ${t(`item.${r.item}`)} · ${dateTime(r.time)}`;
                  return (
                    <tr key={r.event_id}>
                      <td>
                        {r.snapshot_url ? (
                          <button className="thumb" onClick={() => setZoom({ src: url(r.snapshot_url), caption })}
                            aria-label={caption}>
                            <img src={url(r.snapshot_url)} alt="" loading="lazy" />
                          </button>
                        ) : <span className="thumb-none">{t('alerts.noSnapshot')}</span>}
                      </td>
                      <td className="num" style={{ textAlign: 'start' }}>
                        {dateTime(r.time)}
                        <div className="faint small mono">{r.event_id}</div>
                      </td>
                      <td>{t('person', { id: r.person_id })}</td>
                      <td><ItemTag item={r.item} /></td>
                      <td>{t(`change.${r.change}`)}</td>
                      <td>
                        {r.ended_at
                          ? <span className="badge badge-ok">{t('alerts.fixedIn', { d: duration(r.duration_s) })}</span>
                          : <span className="badge badge-bad">{t('alerts.stillOpen')}</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {zoom && <Lightbox {...zoom} onClose={() => setZoom(null)} />}
    </>
  );
}
