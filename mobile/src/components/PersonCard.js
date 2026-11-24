import { StyleSheet, Text, View } from 'react-native';
import { colors, ITEMS, stateColor } from '../theme';

export default function PersonCard({ person }) {
  const anyBad = Object.values(person.items).includes('violation');
  return (
    <View style={[styles.card, anyBad && styles.cardBad]}>
      <Text style={styles.title}>Person {person.id}</Text>
      <View style={styles.row}>
        {ITEMS.map(({ key, label }) => {
          const s = person.items[key] || 'unknown';
          return (
            <View key={key} style={styles.item}>
              <View style={[styles.dot, { backgroundColor: stateColor(s) }]} />
              <Text style={styles.label}>{label}</Text>
              <Text style={[styles.state, { color: stateColor(s) }]}>{s}</Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardBad: { borderColor: colors.violation, borderWidth: 2 },
  title: { fontSize: 16, fontWeight: '700', color: colors.text, marginBottom: 8 },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  item: { alignItems: 'center', flex: 1 },
  dot: { width: 22, height: 22, borderRadius: 11, marginBottom: 4 },
  label: { fontSize: 12, color: colors.text },
  state: { fontSize: 11, fontWeight: '600' },
});
