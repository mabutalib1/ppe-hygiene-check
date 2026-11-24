import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { fetchHealth, normalizeUrl, saveServerUrl } from '../api';
import { colors } from '../theme';

export default function ConnectScreen({ initialUrl, onConnected }) {
  const [input, setInput] = useState(initialUrl || '');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const test = async () => {
    const url = normalizeUrl(input);
    if (!url) return;
    setBusy(true);
    setResult(null);
    try {
      const h = await fetchHealth(url);
      setResult({ ok: true, h });
      await saveServerUrl(url);
      onConnected(url);
    } catch (e) {
      setResult({ ok: false, error: String(e.message || e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.wrap}>
      <Text style={styles.title}>Connect to Check</Text>
      <Text style={styles.hint}>
        Enter the backend address shown on the laptop, e.g. 192.168.1.20:8000. Phone and laptop
        must be on the same Wi-Fi or hotspot.
      </Text>
      <TextInput
        style={styles.input}
        value={input}
        onChangeText={setInput}
        placeholder="192.168.1.20:8000"
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        onSubmitEditing={test}
      />
      <Pressable style={[styles.button, busy && { opacity: 0.6 }]} onPress={test} disabled={busy}>
        {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Test connection</Text>}
      </Pressable>
      {result && !result.ok && (
        <Text style={styles.error}>Could not reach the server: {result.error}</Text>
      )}
      {result?.ok && !result.h.ok && (
        <Text style={styles.warn}>
          Connected, but the server reports a problem: {result.h.error || 'camera not connected'}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, padding: 24, justifyContent: 'center', backgroundColor: colors.bg },
  title: { fontSize: 26, fontWeight: '800', color: colors.text, marginBottom: 8 },
  hint: { fontSize: 14, color: colors.muted, marginBottom: 20, lineHeight: 20 },
  input: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    marginBottom: 12,
  },
  button: { backgroundColor: colors.primary, borderRadius: 10, padding: 14, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  error: { color: colors.violation, marginTop: 14 },
  warn: { color: colors.warnText, marginTop: 14 },
});
