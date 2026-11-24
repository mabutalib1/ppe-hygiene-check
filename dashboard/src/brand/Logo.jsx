import './logo.css';

/**
 * شيّك: the logo (from shayyek-logo-animated.html).
 *
 *   size     px per em: 10 ≈ 520px wide, 2 ≈ 104px (sidebar), 1.3 ≈ 68px (phone top bar)
 *   tagline  'none' | 'mono' (SHAYYEK · AI HYGIENE CHECK) | 'full' (+ نشيّك، وأنت تطمّن)
 *   intro    play the corners → word → check sequence once on mount
 *   live     loop the scan line and chip pulse (only where motion is welcome)
 */
const CORNER = 'M8 4 H40 A20 20 0 0 1 60 24 V56';

export default function Logo({ size = 2, tagline = 'none', intro = false, live = false }) {
  const cls = ['shy', tagline !== 'full' && 'shy--compact', intro && 'shy--intro', live && 'shy--live']
    .filter(Boolean).join(' ');
  return (
    <span className={cls} style={{ fontSize: `${size}px` }} role="img"
      aria-label="شيّك · Shayyek">
      <span className="shy-frame">
        {['tr', 'tl', 'br', 'bl'].map((c) => (
          <span key={c} className={`shy-corner ${c}`} aria-hidden="true">
            <svg viewBox="0 0 64 64"><path d={CORNER} /></svg>
          </span>
        ))}
        <span className="shy-tick r" aria-hidden="true" />
        <span className="shy-tick l" aria-hidden="true" />
        {live && <span className="shy-scan" aria-hidden="true" />}
        <span className="shy-chip" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path className="shy-check" d="M4 12.5 L9.5 18 L20 6.5" /></svg>
        </span>
        <span className="shy-word" aria-hidden="true">شيّك</span>
      </span>
      {tagline !== 'none' && (
        <span className="shy-tag" aria-hidden="true">
          {tagline === 'full' && <span className="shy-line">نشيّك، وأنت تطمّن</span>}
          <span className="shy-mono">SHAYYEK · AI HYGIENE CHECK</span>
        </span>
      )}
    </span>
  );
}

/** Just the mark (corners + check), for tight spots and the favicon. */
export function LogoMark({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" className="logo-mark">
      <g fill="none" stroke="var(--brand)" strokeWidth="6" strokeLinecap="round">
        <path d="M6 22V14a8 8 0 0 1 8-8h8M42 6h8a8 8 0 0 1 8 8v8M58 42v8a8 8 0 0 1-8 8h-8M22 58h-8a8 8 0 0 1-8-8v-8" />
      </g>
      <path d="M20 33l8 8 16-17" fill="none" stroke="var(--brand)" strokeWidth="6.5"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
