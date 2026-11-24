import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, BellRing, CircleAlert, CircleCheck, Gauge, ShieldCheck, Users, VideoOff, WifiOff } from 'lucide-react';
import { ITEMS, meetsFps, url, usePoll } from '../lib/api';
import { useI18n } from '../lib/i18n';
import { useLive } from '../lib/live';
import { Card, EmptyState, ItemTag, Kpi, Lightbox, StatePill } from '../components/ui';

export default function LivePage() {
  const { t, num } = useI18n();
  const { conn, people, fps, feed, health } = useLive();
  const latest = feed[0]?.event_id || '';
  const stats = usePoll(`/stats?days=1&_=${latest}`, 15000);
  const openViolations = people.reduce(
    (n, p) => n + Object.values(p.items).filter((s) => s === 'violation').length, 0);

  return (
    <>
      {conn === 'offline' && <OfflineBanner />}
      <div className="grid kpis">
        <Kpi icon={Users} label={t('live.people')} value={num(people.length)} />
        <Kpi icon={CircleAlert} label={t('live.openViolations')} value={num(openViolations)}
          tone={openViolations ? 'bad' : undefined} />
        <Kpi icon={BellRing} label={t('live.alertsToday')} value={num(stats.data?.total ?? null)} />
        <Kpi icon={Gauge} label={t('live.fps')} value={num(fps)}
          tone={fps && !meetsFps(fps) ? 'warn' : undefined} sub={t('eval.goal.fps')} />
      </div>

      <div className="live-layout" style={{ marginTop: 16 }}>
        <div className="live-main">
          <Stream cameraName={health?.camera?.name} fps={fps} online={conn === 'live'} />
          <Card title={t('live.staff')}>
            {people.length === 0 ? (
              <EmptyState icon={Users} title={t('live.nobody')} hint={t('live.nobodyHint')} />
            ) : (
              <div className="people">
                {people.map((p) => <PersonCard key={p.id} person={p} />)}
              </div>
            )}
          </Card>
        </div>
        <div className="live-side">
          <StatusBanner people={people} open={openViolations} online={conn === 'live'} />
          <Card title={t('live.feed')} action={
            <a className="btn" href="#/alerts">{t('live.seeAll')}<ArrowUpRight size={15} className="flip-rtl" /></a>
          }>
            <Feed feed={feed} />
          </Card>
        </div>
      </div>
    </>
  );
}

export function OfflineBanner() {
  const { t } = useI18n();
  return (
    <div className="banner" role="status">
      <WifiOff size={18} aria-hidden="true" />
      <div>
        {t('conn.offline')} <span className="muted">· {t('conn.offlineHint')}</span>
      </div>
    </div>
  );
}

function Stream({ cameraName, fps, online }) {
  const { t, num } = useI18n();
  const [attempt, setAttempt] = useState(0);
  const [ok, setOk] = useState(false);

  // retry the MJPEG stream every few seconds while it is down
  useEffect(() => {
    if (ok || !online) return undefined;
    const id = setTimeout(() => setAttempt((a) => a + 1), 3000);
    return () => clearTimeout(id);
  }, [ok, online, attempt]);

  return (
    <div className="stream">
      {online && (
        <img key={attempt} src={`${url('/stream')}?a=${attempt}`} alt={t('live.camera')}
          onLoad={() => setOk(true)} onError={() => setOk(false)}
          style={{ visibility: ok ? 'visible' : 'hidden' }} />
      )}
      {(!ok || !online) && (
        <div className="stream-off">
          <VideoOff size={28} aria-hidden="true" />
          <strong>{t('live.streamOff')}</strong>
          <p className="small">{t('live.streamOffHint')}</p>
        </div>
      )}
      <div className="stream-corners" aria-hidden="true">
        {['tr', 'tl', 'br', 'bl'].map((c) => (
          <svg key={c} className={c} viewBox="0 0 64 64"><path d="M8 4 H40 A20 20 0 0 1 60 24 V56" /></svg>
        ))}
      </div>
      {ok && online && (
        <div className="stream-overlay">
          <span className="stream-chip"><span className="rec" />{cameraName || t('live.camera')}</span>
          <span className="stream-chip num" dir="ltr">{num(fps)} fps</span>
        </div>
      )}
    </div>
  );
}

function PersonCard({ person }) {
  const { t } = useI18n();
  const bad = Object.values(person.items).includes('violation');
  return (
    <div className={`person ${bad ? 'bad' : ''}`}>
      <div className="person-head">
        <div className="person-name">
          <span className="avatar">{person.id}</span>
          {t('person', { id: person.id })}
        </div>
        {bad ? <CircleAlert size={18} color="var(--bad)" aria-hidden="true" /> : null}
      </div>
      <div className="person-items">
        {ITEMS.map((item) => (
          <div className="person-item" key={item}>
            <ItemTag item={item} />
            <StatePill state={person.items[item] || 'unknown'} />
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusBanner({ people, open, online }) {
  const { t, num } = useI18n();
  if (!online || people.length === 0) {
    return <div className="status-banner idle"><ShieldCheck size={18} />{t('live.nobody')}</div>;
  }
  if (open) {
    return (
      <div className="status-banner bad" role="alert">
        <CircleAlert size={18} />{t('live.needsAttention')} · {num(open)}
      </div>
    );
  }
  return <div className="status-banner ok"><CircleCheck size={18} />{t('live.allClear')}</div>;
}

export function Feed({ feed }) {
  const { t, time, duration, ago } = useI18n();
  const [zoom, setZoom] = useState(null);
  const seen = useRef(new Set(feed.map((e) => e.event_id)));
  const [, tick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 30000); // refresh "x min ago"
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    feed.forEach((e) => seen.current.add(e.event_id));
  }, [feed]);

  if (feed.length === 0) {
    return <EmptyState icon={BellRing} title={t('live.feedEmpty')} hint={t('live.feedEmptyHint')} />;
  }
  return (
    <>
      <ul className="feed">
        {feed.slice(0, 12).map((e) => {
          const caption = `${t('person', { id: e.person_id })} · ${t(`item.${e.item}`)} · ${time(e.time)}`;
          return (
            <li key={e.event_id} className={seen.current.has(e.event_id) ? '' : 'new'}>
              {e.snapshot_url ? (
                <button className="feed-thumb" onClick={() => setZoom({ src: url(e.snapshot_url), caption })}
                  aria-label={caption}>
                  <img src={url(e.snapshot_url)} alt="" loading="lazy" />
                </button>
              ) : <span className="feed-thumb" />}
              <div className="feed-text">
                <div className="feed-title">
                  <ItemTag item={e.item} />
                  <span className="faint">·</span>
                  <span>{t(`change.${e.change}`)}</span>
                </div>
                <div className="feed-meta">
                  <span>{t('person', { id: e.person_id })}</span>
                  <span title={time(e.time)}>{ago(e.time)}</span>
                  {e.ended_at
                    ? <span className="badge badge-ok">{t('alerts.fixedIn', { d: duration(e.duration_s) })}</span>
                    : <span className="badge badge-bad">{t('alerts.stillOpen')}</span>}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
      {zoom && <Lightbox {...zoom} onClose={() => setZoom(null)} />}
    </>
  );
}
