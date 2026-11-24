import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchEvents, wsUrl } from './api';
import { notifyViolation } from './notify';

const RETRY_MS = 2000;

/**
 * One WebSocket to /ws. Status messages update `people`; violation and
 * resolved events update `events` (newest first) and fire a local notification.
 * Reconnects every 2 s if the connection drops.
 */
export function useBackend(baseUrl) {
  const [connected, setConnected] = useState(false);
  const [people, setPeople] = useState([]);
  const [fps, setFps] = useState(0);
  const [events, setEvents] = useState([]);
  const wsRef = useRef(null);
  const retryRef = useRef(null);
  const aliveRef = useRef(true);

  const refreshEvents = useCallback(async () => {
    if (!baseUrl) return;
    try {
      setEvents(await fetchEvents(baseUrl, 50));
    } catch {}
  }, [baseUrl]);

  const handleMessage = useCallback((msg) => {
    if (msg.type === 'status') {
      setPeople(msg.people || []);
      setFps(msg.fps || 0);
    } else if (msg.type === 'violation') {
      setEvents((prev) => [{ ...msg, ended_at: null, duration_s: null }, ...prev].slice(0, 200));
      notifyViolation(msg);
    } else if (msg.type === 'resolved') {
      setEvents((prev) =>
        prev.map((e) =>
          e.event_id === msg.event_id ? { ...e, ended_at: msg.time, duration_s: msg.duration_s } : e
        )
      );
    }
  }, []);

  useEffect(() => {
    aliveRef.current = true;
    if (!baseUrl) return undefined;

    const connect = () => {
      if (!aliveRef.current) return;
      const ws = new WebSocket(wsUrl(baseUrl));
      wsRef.current = ws;
      ws.onopen = () => {
        setConnected(true);
        refreshEvents(); // fill in anything missed while disconnected
      };
      ws.onmessage = (e) => {
        try {
          handleMessage(JSON.parse(e.data));
        } catch {}
      };
      ws.onerror = () => {};
      ws.onclose = () => {
        setConnected(false);
        if (aliveRef.current) retryRef.current = setTimeout(connect, RETRY_MS);
      };
    };

    connect();
    return () => {
      aliveRef.current = false;
      clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, [baseUrl, handleMessage, refreshEvents]);

  return { connected, people, fps, events, refreshEvents };
}
