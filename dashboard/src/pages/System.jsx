import { Brain, Camera, Gauge, Server } from 'lucide-react';
import { meetsFps, url, usePoll } from '../lib/api';
import { useI18n } from '../lib/i18n';
import { useLive } from '../lib/live';
import { Card, PageHeader, Skeleton } from '../components/ui';
import { OfflineBanner } from './Live';

const UNITS = { window_s: 's', decide_after_s: 's', cooldown_s: 's', lost_after_s: 's', reentry_s: 's' };

export default function SystemPage() {
  const { t, num } = useI18n();
  const { health, conn, fps } = useLive();
  const config = usePoll('/config', 30000);
  const engine = config.data?.engine;
  const h = health;

  return (
    <>
      {conn === 'offline' && <OfflineBanner />}
      <PageHeader title={t('sys.title')} subtitle={t('sys.subtitle')} />

      <div className="grid kpis">
        <Health icon={Server} title={t('sys.server')} ok={conn === 'live'}
          main={conn === 'live' ? t('conn.live') : t('conn.offline')}
          sub={h ? t('sys.version', { v: h.version }) : null} />
        <Health icon={Camera} title={t('sys.camera')} ok={h?.camera?.connected}
          main={h ? (h.camera.connected ? t('sys.connected') : t('sys.disconnected')) : '–'}
          sub={h?.camera?.last_frame_age_s != null ? t('sys.frameAge', { s: num(h.camera.last_frame_age_s) }) : h?.camera?.source}
          mono={h?.camera?.source} />
        <Health icon={Brain} title={t('sys.model')} ok={h?.model?.loaded}
          main={h ? (h.model.loaded ? t('sys.loaded') : t('sys.notLoaded')) : '–'}
          sub={h?.model ? (h.model.detector === 'fake' ? t('model.fake') : t('model.yolo')) : null}
          error={h?.model?.error} />
        <Health icon={Gauge} title={t('sys.speed')} ok={meetsFps(fps)} warn={fps > 0 && !meetsFps(fps)}
          main={<span dir="ltr">{num(fps)} fps</span>} sub={`${t('eval.goals')}: ${t('eval.goal.fps')}`} error={h?.error && !h?.model?.error ? h.error : null} />
      </div>

      <Card title={t('sys.rules')} subtitle={t('sys.rulesHint')} pad={false}>
        {!engine ? <div className="card-body"><Skeleton h={200} /></div> : (
          <div className="table-wrap">
            <table>
              <tbody>
                {Object.entries(engine).map(([k, v]) => (
                  <tr key={k}>
                    <td className="mono small" style={{ whiteSpace: 'nowrap' }}>CHECK_{k.toUpperCase()}</td>
                    <td className="muted">{t(`cfg.${k}`)}</td>
                    <td className="num"><strong>{num(v)}{UNITS[k] ? ` ${UNITS[k]}` : ''}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title={t('sys.api')}>
        <div className="api-links mono small">
          {['/health', '/config', '/stats', '/events', '/training/results', '/evaluation/results', '/dataset/summary', '/stream', '/docs'].map((p) => (
            <a key={p} href={url(p)} target="_blank" rel="noreferrer">{p}</a>
          ))}
        </div>
      </Card>
    </>
  );
}

function Health({ icon: Icon, title, ok, warn, main, sub, error, mono }) {
  const { t } = useI18n();
  const tone = ok ? 'badge-ok' : warn ? 'badge-warn' : 'badge-bad';
  return (
    <div className="kpi health">
      <div className="health-top">
        <span className="health-title"><Icon size={16} aria-hidden="true" />{title}</span>
        <span className={`badge ${tone}`}>●</span>
      </div>
      <div className="health-main">{main}</div>
      {sub && <div className={`kpi-sub ${mono && sub === mono ? 'mono' : ''}`}>{sub}</div>}
      {error && <div className="health-err" title={error}>{t('sys.error')}: {error}</div>}
    </div>
  );
}
