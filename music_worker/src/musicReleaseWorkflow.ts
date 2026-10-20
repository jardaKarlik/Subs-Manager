import { proxyActivities } from '@temporalio/workflow';
import type * as activities from './musicReleaseActivities.js';

const acts = proxyActivities<typeof activities>({
  startToCloseTimeout: '5 minutes',
  retry: { maximumAttempts: 3 },
});

export interface MusicReleaseScanResult {
  bandcamp: number;
  soundcloud: number;
  inserted: number;
  skipped: number;
  notified: boolean;
}

/**
 * Daily music release scan: pull Bandcamp (Outlook/Composio) + SoundCloud
 * releases and persist new rows to the Releases database.
 * Deterministic: all I/O and Date usage happens in activities.
 */
export const musicReleaseScanWorkflow = async (): Promise<MusicReleaseScanResult> => {
  const bandcamp = await acts.fetchBandcampReleasesActivity();
  const soundcloud = await acts.fetchSoundcloudReleasesActivity();
  const merged = [...bandcamp, ...soundcloud];
  const persisted = await acts.persistMusicReleasesActivity(merged);
  const notified = await acts.notifyMusicScanActivity({
    bandcamp: bandcamp.length,
    soundcloud: soundcloud.length,
    inserted: persisted.inserted,
    skipped: persisted.skipped,
  });
  return {
    bandcamp: bandcamp.length,
    soundcloud: soundcloud.length,
    inserted: persisted.inserted,
    skipped: persisted.skipped,
    notified: notified.sent,
  };
};