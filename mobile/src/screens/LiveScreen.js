import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { WebView } from 'react-native-webview';
import PersonCard from '../components/PersonCard';
import { streamUrl } from '../api';
import { colors } from '../theme';

// React Native's Image doesn't reliably play MJPEG, so the stream lives in a WebView
const streamHtml = (url) => `<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<style>html,body{margin:0;background:#000;height:100%;display:flex;align-items:center;justify-content:center}
img{width:100%;height:100%;object-fit:contain}</style></head>
<body><img src="${url}"/></body></html>`;

export default function LiveScreen({ baseUrl, people, fps, connected }) {
  return (
    <View style={styles.wrap}>
      <View style={styles.video}>
        <WebView
          key={connected ? 'on' : 'off'} // reload the stream after a reconnect
          source={{ html: streamHtml(streamUrl(baseUrl)) }}
          originWhitelist={['*']}
          style={{ backgroundColor: '#000' }}
          scrollEnabled={false}
          mixedContentMode="always"
        />
      </View>
      <View style={styles.header}>
        <Text style={styles.h}>On camera: {people.length}</Text>
        <Text style={styles.fps}>{fps ? `${fps} fps` : ''}</Text>
      </View>
      <ScrollView contentContainerStyle={styles.list}>
        {people.length === 0 ? (
          <Text style={styles.empty}>No one in view.</Text>
        ) : (
          people.map((p) => <PersonCard key={p.id} person={p} />)
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: colors.bg },
  video: { aspectRatio: 16 / 9, width: '100%', backgroundColor: '#000' },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 4,
  },
  h: { fontSize: 15, fontWeight: '700', color: colors.text },
  fps: { fontSize: 13, color: colors.muted },
  list: { padding: 16, paddingTop: 8 },
  empty: { color: colors.muted, textAlign: 'center', marginTop: 20 },
});
