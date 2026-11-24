import { useEffect, useState } from 'react';
import {
  BellRing, Brain, ChartColumn, CircleAlert, CircleCheck, FlaskConical, Languages,
  Server, Video, Volume2, VolumeX, X,
} from 'lucide-react';
import Logo from './brand/Logo';
import ItemIcon from './brand/ItemIcon';
import { TokensContext } from './components/ui';
import { useI18n } from './lib/i18n';
import { useLive } from './lib/live';
import { useTokens } from './lib/theme';
import LivePage from './pages/Live';
import AlertsPage from './pages/Alerts';
import InsightsPage from './pages/Insights';
import ModelPage from './pages/Model';
import EvaluationPage from './pages/Evaluation';
import SystemPage from './pages/System';

const PAGES = {
  live: { icon: Video, Page: LivePage, section: 'monitor' },
  alerts: { icon: BellRing, Page: AlertsPage, section: 'monitor' },
  insights: { icon: ChartColumn, Page: InsightsPage, section: 'monitor' },
  model: { icon: Brain, Page: ModelPage, section: 'project' },
  evaluation: { icon: FlaskConical, Page: EvaluationPage, section: 'project' },
  system: { icon: Server, Page: SystemPage, section: 'project' },
};

function useRoute() {
  const get = () => {
    const r = window.location.hash.replace(/^#\/?/, '');
    return PAGES[r] ? r : 'live';
  };
  const [route, setRoute] = useState(get);
  useEffect(() => {
    const on = () => {
      setRoute(get());
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  return route;
}

export default function App() {
  const route = useRoute();
  const tokens = useTokens();
  const { t, toggle: toggleLang, lang } = useI18n();
  const live = useLive();
  const { Page } = PAGES[route];

  return (
    <TokensContext.Provider value={tokens}>
      <div className="shell">
        <aside className="sidebar">
          <a className="sidebar-logo" href="#/live" aria-label="Shayyek">
            <Logo size={2.1} intro />
            <span className="tagline">AI HYGIENE CHECK</span>
          </a>
          <nav aria-label="Main">
            {['monitor', 'project'].map((section) => (
              <div className="nav-section" key={section}>
                <div className="nav-label">{t(`nav.section.${section}`)}</div>
                {Object.entries(PAGES).filter(([, p]) => p.section === section).map(([key, { icon: Icon }]) => (
                  <a key={key} href={`#/${key}`} className={`nav-link ${route === key ? 'active' : ''}`}
                    aria-current={route === key ? 'page' : undefined}>
                    <Icon size={18} aria-hidden="true" />
                    <span>{t(`nav.${key}`)}</span>
                    {key === 'alerts' && live.feed.some((e) => !e.ended_at) && <span className="nav-dot" />}
                  </a>
                ))}
              </div>
            ))}
          </nav>
          <div className="sidebar-foot">
            <ConnBadge />
          </div>
        </aside>

        <div className="main">
          <header className="topbar">
            <a className="topbar-logo" href="#/live" aria-label="Shayyek"><Logo size={1.2} /></a>
            <div className="topbar-status">
              <ConnBadge />
              {live.demo && (
                <span className="badge badge-warn" title={t('demo.hint')}>{t('demo.badge')}</span>
              )}
            </div>
            <div className="topbar-actions">
              <button className="icon-btn" onClick={live.toggleSound}
                title={live.sound ? t('sound.on') : t('sound.off')} aria-label={live.sound ? t('sound.on') : t('sound.off')}>
                {live.sound ? <Volume2 size={18} /> : <VolumeX size={18} />}
              </button>
              <button className={`lang-btn ${lang === 'en' ? 'to-ar' : ''}`} onClick={toggleLang}>
                <Languages size={16} aria-hidden="true" />
                {t('lang.toggle')}
              </button>
            </div>
          </header>
          <nav className="mobile-nav" aria-label="Main">
            {Object.entries(PAGES).map(([key, { icon: Icon }]) => (
              <a key={key} href={`#/${key}`} className={route === key ? 'active' : ''}
                aria-current={route === key ? 'page' : undefined}>
                <Icon size={17} aria-hidden="true" />
                {t(`nav.${key}`)}
              </a>
            ))}
          </nav>
          <main className="content" key={route}>
            <Page />
          </main>
        </div>
        <Toaster />
      </div>
    </TokensContext.Provider>
  );
}

function ConnBadge() {
  const { conn } = useLive();
  const { t } = useI18n();
  return (
    <span className={`conn conn-${conn}`} title={conn === 'offline' ? t('conn.offlineHint') : undefined}>
      <span className="conn-dot" />
      {t(`conn.${conn}`)}
    </span>
  );
}

function Toaster() {
  const { toasts, dismiss } = useLive();
  const { t } = useI18n();
  return (
    <div className="toaster" aria-live="polite">
      {toasts.map(({ id, ev }) => {
        const bad = ev.type === 'violation';
        const person = t('person', { id: ev.person_id });
        const item = t(`item.${ev.item}`);
        return (
          <div key={id} className={`toast ${bad ? 'toast-bad' : 'toast-ok'}`} role={bad ? 'alert' : 'status'}>
            <span className="toast-icon">{bad ? <CircleAlert size={18} /> : <CircleCheck size={18} />}</span>
            <span className="toast-item"><ItemIcon item={ev.item} size={18} /></span>
            <span className="toast-text">
              {bad
                ? t('toast.violation', { person, item, change: t(`change.${ev.change}`) })
                : t('toast.resolved', { person, item, s: Math.round(ev.duration_s) })}
            </span>
            <button className="icon-btn small" onClick={() => dismiss(id)} aria-label={t('close')}><X size={14} /></button>
          </div>
        );
      })}
    </div>
  );
}
