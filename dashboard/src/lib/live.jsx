import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { getJson, usePoll, wsUrl } from './api';
import { load, save } from './storage';

/**
 * One WebSocket for the whole dashboard. Holds the live people status, fps,
 * a feed of recent events, backend health, and pop-up toasts.
 */
const Live = createContext(null);
const FEED_MAX = 40;

function beep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = 'sine';
    o.frequency.value = 880;
    g.gain.setValueAtTime(0.0001, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.35);
    o.connect(g).connect(ctx.destination);
    o.start();
    o.stop(ctx.currentTime + 0.4);
    o.onended = () => ctx.close();
  } catch {
    /* no audio available */
  }
}

export function LiveProvider({ children }) {
  const [conn, setConn] = useState('connecting'); // connecting | live | offline
  const [people, setPeople] = useState([]);
  const [fps, setFps] = useState(0);
  const [feed, setFeed] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [sound, setSound] = useState(() => load('check.sound') !== 'off');
  const soundRef = useRef(sound);
  const health = usePoll('/health', 3000);

  useEffect(() => {
    soundRef.current = sound;
    save('check.sound', sound ? 'on' : 'off');
  }, [sound]);

  const dismiss = useCallback((id) => setToasts((ts) => ts.filter((x) => x.id !== id)), []);
  const pushToast = useCallback((ev) => {
    const id = `${ev.type}-${ev.event_id}-${Date.now()}`;
    setToasts((ts) => [...ts.slice(-3), { id, ev }]);
    setTimeout(() => dismiss(id), ev.type === 'violation' ? 8000 : 5000);
  }, [dismiss]);

  // seed the feed from history, then keep it live over the socket
  const seed = useCallback(async () => {
    try {
      setFeed(await getJson('/events?limit=20'));
    } catch {
      /* offline: the socket loop retries */
    }
  }, []);

  useEffect(() => {
    let ws;
    let stopped = false;
    let retry;
    let delay = 1000;

    const connect = () => {
      setConn((c) => (c === 'live' ? 'connecting' : c));
      ws = new WebSocket(wsUrl());
      ws.onopen = () => {
        delay = 1000;
        setConn('live');
        seed();
      };
      ws.onmessage = (m) => {
        let msg;
        try {
          msg = JSON.parse(m.data);
        } catch {
          return;
        }
        if (msg.type === 'status') {
          setPeople(msg.people || []);
          setFps(msg.fps || 0);
        } else if (msg.type === 'violation') {
          setFeed((f) => [{ ...msg, ended_at: null, duration_s: null }, ...f.filter((e) => e.event_id !== msg.event_id)].slice(0, FEED_MAX));
          pushToast(msg);
          if (soundRef.current) beep();
        } else if (msg.type === 'resolved') {
          setFeed((f) => f.map((e) => (e.event_id === msg.event_id ? { ...e, ended_at: msg.time, duration_s: msg.duration_s } : e)));
          pushToast(msg);
        }
      };
      ws.onclose = () => {
        if (stopped) return;
        setConn('offline');
        setPeople([]);
        setFps(0);
        retry = setTimeout(connect, delay);
        delay = Math.min(delay * 2, 10000);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      stopped = true;
      clearTimeout(retry);
      ws?.close();
    };
  }, [seed, pushToast]);

  const value = {
    conn, people, fps, feed, toasts, dismiss, sound,
    toggleSound: () => setSound((s) => !s),
    health: health.data,
    demo: health.data?.model?.detector === 'fake',
  };
  return <Live.Provider value={value}>{children}</Live.Provider>;
}

export const useLive = () => useContext(Live);
