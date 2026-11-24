/**
 * Backend access. By default the dashboard talks to the server that serves it
 * (same origin). Set VITE_API_URL at build time to point it somewhere else.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export const API = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');
export const ITEMS = ['mask', 'hairnet', 'gloves'];
export const CLASSES = ['person', 'hairnet', 'no_hairnet', 'mask', 'no_mask', 'gloves', 'no_gloves'];

// Live speed goal. The backend caps at TARGET_FPS=10, so ~9.7 measured counts as meeting it.
export const FPS_GOAL = 10;
export const meetsFps = (fps) => Math.round(fps) >= FPS_GOAL;

export const url = (path) => `${API}${path}`;
export const wsUrl = () => {
  const base = API || window.location.origin;
  return `${base.replace(/^http/i, 'ws')}/ws`;
};

export async function getJson(path, timeoutMs = 5000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url(path), { signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

/** Fetch `path` now and every `intervalMs` (0 = once). Keeps the last good data on errors. */
export function usePoll(path, intervalMs = 0) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const alive = useRef(true);

  const refresh = useCallback(async () => {
    if (!path) return;
    try {
      const data = await getJson(path);
      if (alive.current) setState({ data, error: null, loading: false });
    } catch (error) {
      if (alive.current) setState((s) => ({ ...s, error, loading: false }));
    }
  }, [path]);

  useEffect(() => {
    alive.current = true;
    setState((s) => ({ ...s, loading: true }));
    refresh();
    const id = intervalMs ? setInterval(refresh, intervalMs) : null;
    return () => {
      alive.current = false;
      if (id) clearInterval(id);
    };
  }, [refresh, intervalMs]);

  return { ...state, refresh };
}
