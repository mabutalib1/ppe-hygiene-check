import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';

export default function TabBar({ tabs, active, onChange, bottomInset = 0 }) {
  return (
    <View style={[styles.bar, { paddingBottom: Math.max(bottomInset, 8) }]}>
      {tabs.map((t) => {
        const on = t.key === active;
        return (
          <Pressable key={t.key} style={styles.tab} onPress={() => onChange(t.key)}>
            <Text style={[styles.text, on && styles.textOn]}>
              {t.label}
              {t.badge ? `  (${t.badge})` : ''}
            </Text>
            <View style={[styles.underline, on && styles.underlineOn]} />
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    backgroundColor: colors.card,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: 8,
  },
  tab: { flex: 1, alignItems: 'center' },
  text: { fontSize: 15, color: colors.muted, fontWeight: '600' },
  textOn: { color: colors.primary },
  underline: { height: 3, width: 28, marginTop: 6, borderRadius: 2 },
  underlineOn: { backgroundColor: colors.primary },
});
