export const colors = {
  bg: '#F5F6F8',
  card: '#FFFFFF',
  text: '#1B1F24',
  muted: '#6B7280',
  border: '#E5E7EB',
  primary: '#1F6FEB',
  ok: '#2EA043',
  violation: '#D73A49',
  unknown: '#9CA3AF',
  warnBg: '#FFF4E5',
  warnText: '#8A4B00',
};

export const stateColor = (s) =>
  s === 'ok' ? colors.ok : s === 'violation' ? colors.violation : colors.unknown;

export const ITEMS = [
  { key: 'mask', label: 'Mask' },
  { key: 'hairnet', label: 'Hairnet' },
  { key: 'gloves', label: 'Gloves' },
  { key: 'uniform', label: 'Uniform' },
];

export const itemLabel = (k) => ITEMS.find((i) => i.key === k)?.label ?? k;
