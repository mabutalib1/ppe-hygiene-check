import { useEffect, useState } from 'react';
import {
  FlatList, Image, Modal, Pressable, RefreshControl, StyleSheet, Text, View,
} from 'react-native';
import { snapshotUrl } from '../api';
import { describeEvent } from '../notify';
import { colors } from '../theme';

const fmtTime = (iso) => {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return iso;
  }
};

function AlertRow({ ev, baseUrl, onPress }) {
  const uri = snapshotUrl(baseUrl, ev.snapshot_url);
  const open = ev.duration_s == null;
  return (
    <Pressable style={styles.row} onPress={onPress}>
      {uri ? <Image source={{ uri }} style={styles.thumb} /> : <View style={[styles.thumb, styles.noThumb]} />}
      <View style={{ flex: 1 }}>
        <Text style={styles.title}>{describeEvent(ev)}</Text>
        <Text style={styles.meta}>
          {fmtTime(ev.time)} · {open ? 'ongoing' : `lasted ${Math.round(ev.duration_s)} s`}
        </Text>
      </View>
      <View style={[styles.pill, { backgroundColor: open ? colors.violation : colors.ok }]} />
    </Pressable>
  );
}

export default function AlertsScreen({ baseUrl, events, refreshEvents }) {
  const [refreshing, setRefreshing] = useState(false);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    refreshEvents(); // complete history even if the app was closed
  }, [refreshEvents]);

  const onRefresh = async () => {
    setRefreshing(true);
    await refreshEvents();
    setRefreshing(false);
  };

  return (
    <View style={styles.wrap}>
      <FlatList
        data={events}
        keyExtractor={(e) => e.event_id}
        renderItem={({ item }) => (
          <AlertRow ev={item} baseUrl={baseUrl} onPress={() => setSelected(item)} />
        )}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={<Text style={styles.empty}>No alerts yet.</Text>}
        contentContainerStyle={{ padding: 16 }}
      />
      <Modal visible={!!selected} animationType="slide" onRequestClose={() => setSelected(null)}>
        {selected && (
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>{describeEvent(selected)}</Text>
            <Text style={styles.meta}>
              {fmtTime(selected.time)} · {selected.camera}
              {selected.duration_s != null ? ` · lasted ${Math.round(selected.duration_s)} s` : ' · ongoing'}
            </Text>
            {selected.snapshot_url && (
              <Image
                source={{ uri: snapshotUrl(baseUrl, selected.snapshot_url) }}
                style={styles.full}
                resizeMode="contain"
              />
            )}
            <Pressable style={styles.close} onPress={() => setSelected(null)}>
              <Text style={styles.closeText}>Close</Text>
            </Pressable>
          </View>
        )}
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: colors.bg },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 10,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  thumb: { width: 72, height: 48, borderRadius: 6, marginRight: 12, backgroundColor: '#000' },
  noThumb: { backgroundColor: colors.border },
  title: { fontSize: 15, fontWeight: '700', color: colors.text },
  meta: { fontSize: 13, color: colors.muted, marginTop: 2 },
  pill: { width: 10, height: 10, borderRadius: 5, marginLeft: 8 },
  empty: { color: colors.muted, textAlign: 'center', marginTop: 40 },
  modal: { flex: 1, padding: 20, paddingTop: 60, backgroundColor: colors.bg },
  modalTitle: { fontSize: 20, fontWeight: '800', color: colors.text },
  full: { width: '100%', aspectRatio: 16 / 9, marginTop: 16, backgroundColor: '#000', borderRadius: 8 },
  close: { marginTop: 24, backgroundColor: colors.primary, padding: 14, borderRadius: 10, alignItems: 'center' },
  closeText: { color: '#fff', fontWeight: '700', fontSize: 16 },
});
