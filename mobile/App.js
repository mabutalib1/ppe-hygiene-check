import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import { loadServerUrl } from './src/api';
import TabBar from './src/components/TabBar';
import { setupNotifications } from './src/notify';
import AlertsScreen from './src/screens/AlertsScreen';
import ConnectScreen from './src/screens/ConnectScreen';
import LiveScreen from './src/screens/LiveScreen';
import { colors } from './src/theme';
import { useBackend } from './src/useBackend';

function Main({ baseUrl, onChangeServer }) {
  const insets = useSafeAreaInsets();
  const [tab, setTab] = useState('live');
  const { connected, people, fps, events, refreshEvents } = useBackend(baseUrl);
  const openCount = events.filter((e) => e.duration_s == null).length;

  return (
    <View style={[styles.flex, { paddingTop: insets.top }]}>
      <View style={styles.topbar}>
        <Text style={styles.brand}>Check</Text>
        <Pressable onPress={onChangeServer}>
          <Text style={styles.server}>{baseUrl.replace(/^https?:\/\//, '')}</Text>
        </Pressable>
      </View>
      {!connected && (
        <View style={styles.banner}>
          <ActivityIndicator size="small" color={colors.warnText} />
          <Text style={styles.bannerText}>Reconnecting…</Text>
        </View>
      )}
      <View style={styles.flex}>
        {tab === 'live' ? (
          <LiveScreen baseUrl={baseUrl} people={people} fps={fps} connected={connected} />
        ) : (
          <AlertsScreen baseUrl={baseUrl} events={events} refreshEvents={refreshEvents} />
        )}
      </View>
      <TabBar
        tabs={[
          { key: 'live', label: 'Live' },
          { key: 'alerts', label: 'Alerts', badge: openCount || null },
        ]}
        active={tab}
        onChange={setTab}
        bottomInset={insets.bottom}
      />
    </View>
  );
}

function Root() {
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(true);
  const [baseUrl, setBaseUrl] = useState('');
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    setupNotifications();
    loadServerUrl().then((u) => {
      setBaseUrl(u);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <View style={[styles.flex, styles.center]}>
        <ActivityIndicator />
      </View>
    );
  }
  if (!baseUrl || editing) {
    return (
      <View style={[styles.flex, { paddingTop: insets.top }]}>
        <ConnectScreen
          initialUrl={baseUrl}
          onConnected={(u) => {
            setBaseUrl(u);
            setEditing(false);
          }}
        />
      </View>
    );
  }
  return <Main baseUrl={baseUrl} onChangeServer={() => setEditing(true)} />;
}

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <View style={[styles.flex, { backgroundColor: colors.bg }]}>
        <Root />
      </View>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  center: { alignItems: 'center', justifyContent: 'center' },
  topbar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: colors.card,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  brand: { fontSize: 20, fontWeight: '800', color: colors.text },
  server: { fontSize: 13, color: colors.primary },
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.warnBg,
    paddingVertical: 6,
    paddingHorizontal: 16,
  },
  bannerText: { color: colors.warnText, fontWeight: '600' },
});
