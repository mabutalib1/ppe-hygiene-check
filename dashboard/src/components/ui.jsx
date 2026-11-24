import { createContext, useContext, useEffect } from 'react';
import { CircleAlert, CircleCheck, EyeOff, X } from 'lucide-react';
import ItemIcon from '../brand/ItemIcon';
import { useI18n } from '../lib/i18n';

export const TokensContext = createContext({});
export const useChartTokens = () => useContext(TokensContext);

export function PageHeader({ title, subtitle, actions }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function Card({ title, subtitle, action, children, className = '', pad = true }) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <div className="card-head">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p className="muted small">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      <div className={pad ? 'card-body' : ''}>{children}</div>
    </section>
  );
}

export function Kpi({ label, value, sub, tone, icon: Icon }) {
  return (
    <div className={`kpi ${tone ? `tone-${tone}` : ''}`}>
      <div className="kpi-label">
        {Icon && <Icon size={15} aria-hidden="true" />}
        {label}
      </div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

const STATE_ICON = { ok: CircleCheck, violation: CircleAlert, unknown: EyeOff };

export function StatePill({ state, compact }) {
  const { t } = useI18n();
  const Icon = STATE_ICON[state] || EyeOff;
  return (
    <span className={`pill pill-${state}`}>
      <Icon size={13} aria-hidden="true" />
      {!compact && t(`state.${state}`)}
    </span>
  );
}

export function ItemTag({ item }) {
  const { t } = useI18n();
  return (
    <span className={`item-tag item-${item}`}>
      <ItemIcon item={item} size={15} />
      {t(`item.${item}`)}
    </span>
  );
}

export function EmptyState({ icon: Icon, title, hint, children, tone }) {
  return (
    <div className={`empty ${tone ? `tone-${tone}` : ''}`}>
      {Icon && (
        <div className="empty-icon">
          <Icon size={22} aria-hidden="true" />
        </div>
      )}
      <div className="empty-title">{title}</div>
      {hint && <p className="muted">{hint}</p>}
      {children}
    </div>
  );
}

export function Segmented({ value, options, onChange, label }) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={value === o.value}
          className={value === o.value ? 'on' : ''} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Lightbox({ src, caption, onClose }) {
  const { t } = useI18n();
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="lightbox" role="dialog" aria-modal="true" onClick={onClose}>
      <figure onClick={(e) => e.stopPropagation()}>
        <button className="icon-btn lightbox-close" onClick={onClose} aria-label={t('close')}>
          <X size={18} />
        </button>
        <img src={src} alt={caption} />
        {caption && <figcaption>{caption}</figcaption>}
      </figure>
    </div>
  );
}

export function Skeleton({ h = 120 }) {
  return <div className="skeleton" style={{ height: h }} />;
}
