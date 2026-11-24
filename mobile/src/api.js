import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = 'check.serverUrl';

/** "192.168.1.20:8000" → "http://192.168.1.20:8000" (no trailing slash) */
export function normalizeUrl(input) {
  let url = (input || '').trim().replace(/\/+$/, '');
  if (!url) return '';
  if (!/^https?:\/\//i.test(url)) url = `http://${url}`;
  return url;
}

export const wsUrl = (base) => base.replace(/^http/i, 'ws') + '/ws';
export const streamUrl = (base) => `${base}/stream`;
export const snapshotUrl = (base, path) => (path ? `${base}${path}` : null);

async function getJson(url, timeoutMs = 4000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

export const fetchHealth = (base) => getJson(`${base}/health`);
export const fetchEvents = (base, limit = 50) => getJson(`${base}/events?limit=${limit}`);

export async function loadServerUrl() {
  try {
    return (await AsyncStorage.getItem(KEY)) || '';
  } catch {
    return '';
  }
}

export async function saveServerUrl(url) {
  try {
    await AsyncStorage.setItem(KEY, url);
  } catch {}
}
