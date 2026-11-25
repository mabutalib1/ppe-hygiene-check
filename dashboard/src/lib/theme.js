import { useState } from 'react';

/** Read CSS color tokens once so charts (SVG attributes) use the theme colors. */
export function useTokens() {
  const [tokens] = useState(read);
  return tokens;
}

function read() {
  const cs = getComputedStyle(document.documentElement);
  const v = (n) => cs.getPropertyValue(`--${n}`).trim();
  return {
    brand: v('brand'), text: v('text'), text2: v('text-2'), text3: v('text-3'),
    border: v('border'), surface: v('surface'), ok: v('ok'), bad: v('bad'), unk: v('unk'),
    warn: v('warn'), mask: v('item-mask'), gloves: v('item-gloves'),
  };
}
