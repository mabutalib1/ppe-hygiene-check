import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { itemLabel } from './theme';

// Show alerts with sound even while the app is open
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function setupNotifications() {
  try {
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('violations', {
        name: 'Hygiene violations',
        importance: Notifications.AndroidImportance.HIGH,
        vibrationPattern: [0, 300, 200, 300],
        sound: 'default',
      });
    }
    const { status } = await Notifications.getPermissionsAsync();
    if (status !== 'granted') await Notifications.requestPermissionsAsync();
  } catch (e) {
    console.warn('notifications unavailable', e);
  }
}

export function describeEvent(ev) {
  const item = itemLabel(ev.item).toLowerCase();
  if (ev.change === 'missing') return `Person ${ev.person_id}, entered without ${item}`;
  return `Person ${ev.person_id}, ${item} removed`;
}

/** Local notification: works while the app is open or in the background. */
export async function notifyViolation(ev) {
  try {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: 'Hygiene alert',
        body: describeEvent(ev),
        sound: 'default',
        data: { event_id: ev.event_id },
      },
      trigger: Platform.OS === 'android' ? { channelId: 'violations' } : null,
    });
  } catch (e) {
    console.warn('notify failed', e);
  }
}
