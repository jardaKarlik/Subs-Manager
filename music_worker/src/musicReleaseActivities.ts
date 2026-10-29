import pg from 'pg';
import { loadTeknoConfig } from './config.js';

const { Pool } = pg;

export interface MusicRelease {
  platform: 'bandcamp' | 'soundcloud';
  artist: string;
  track: string;
  url: string;
  emailId: string;
  from: string;
  emailSubject: string;
  emailDate: string;
}

export interface PersistResult {
  candidates: number;
  inserted: number;
  skipped: number;
  dbError?: string | undefined;
}

const MERCH = /\b(poster|sweatshirt|hoodie|t-?shirt|stickers?|tote|mug)\b/i;
const PROMO = /^(activate your account|make a difference|new eu customs fee|discover improvements)/i;

/**
 * Parse a Bandcamp notification subject into artist/track.
 * Real-world shapes:
 *   "New release from X, who brought you Y"  -> artist X, track Y
 *   "New releases from X"                    -> artist X, track Unknown
 *   "New release from X"                     -> artist X, track Unknown
 *   "New from X: Y, Limited Edition ..."     -> artist X, track Y
 *   "Artist - Track"                         -> artist, track
 * "New message from ..." and merch/promo subjects are not releases.
 */
export const parseBandcampSubject = (raw: string): { artist: string; track: string } | null => {
  const subject = (raw ?? '').trim();
  if (!subject) return null;
  if (/^\s*new message\b/i.test(subject)) return null;
  if (/^\s*new (items?)\b/i.test(subject)) return null;
  if (MERCH.test(subject) || PROMO.test(subject)) return null;

  let m = subject.match(/^new releases? from\s+(.+?)(?:,\s*who brought you\s+(.+))?$/i);
  if (m) {
    return { artist: (m[1] ?? '').trim(), track: (m[2] ?? '').trim() || 'Unknown Track' };
  }
  m = subject.match(/^new from\s+(.+?):\s*(.+)$/i);
  if (m) {
    return { artist: (m[1] ?? '').trim(), track: (m[2] ?? '').trim() };
  }
  m = subject.match(/^(.+?)\s*[–-]\s*(.+)$/);
  if (m) {
    return { artist: (m[1] ?? '').trim(), track: (m[2] ?? '').trim() };
  }
  return null;
};

interface OutlookMessage {
  id?: string;
  subject?: string;
  receivedDateTime?: string;
}

interface SoundcloudItem {
  created_at?: string;
  track?: {
    id?: number;
    title?: string;
    permalink_url?: string;
    user?: { username?: string };
  };
}

/**
 * Query Bandcamp release emails via Composio's Outlook tool and parse
 * "Artist – Track" subjects into release records.
 */
export const fetchBandcampReleasesActivity = async (): Promise<MusicRelease[]> => {
  const cfg = loadTeknoConfig();
  if (!cfg.composioApiKey) {
    throw new Error('Missing COMPOSIO_API_KEY for the music release scanner');
  }
  const since = new Date(Date.now() - cfg.bandcampLookbackDays * 24 * 60 * 60 * 1000).toISOString();
  const body = {
    connected_account_id: cfg.composioOutlookAccountId,
    user_id: cfg.composioUserId,
    arguments: {
      filter: `from/emailAddress/address eq 'noreply@bandcamp.com' and receivedDateTime ge ${since} and not startswith(subject, 'Thank you!') and not startswith(subject, 'New item')`,
      folder: 'inbox',
      select: ['id', 'subject', 'from', 'bodyPreview', 'body', 'receivedDateTime'],
      top: 25,
      orderby: 'receivedDateTime desc',
    },
  };
  const res = await fetch('https://backend.composio.dev/api/v3.1/tools/execute/OUTLOOK_QUERY_EMAILS', {
    method: 'POST',
    headers: { 'x-api-key': cfg.composioApiKey, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Composio OUTLOOK_QUERY_EMAILS failed: HTTP ${res.status} ${(await res.text()).slice(0, 300)}`);
  }
  const payload = (await res.json()) as { data?: { value?: OutlookMessage[] } };
  const messages = payload.data?.value ?? [];

  const releases: MusicRelease[] = [];
  for (const item of messages) {
    const subject = item.subject ?? '';
    const parsed = parseBandcampSubject(subject);
    if (!parsed) continue;
    releases.push({
      platform: 'bandcamp',
      artist: parsed.artist,
      track: parsed.track,
      url: subject,
      emailId: item.id ?? '',
      from: 'bandcamp',
      emailSubject: subject,
      emailDate: item.receivedDateTime ?? new Date().toISOString(),
    });
  }
  return releases;
};

/**
 * Query the SoundCloud stream feed and map tracks to release records.
 */
export const fetchSoundcloudReleasesActivity = async (): Promise<MusicRelease[]> => {
  const cfg = loadTeknoConfig();
  if (!cfg.soundcloudClientId) {
    throw new Error('Missing SOUNDCLOUD_CLIENT_ID for the music release scanner');
  }
  const url = `https://api-v2.soundcloud.com/stream?client_id=${encodeURIComponent(cfg.soundcloudClientId)}&limit=20`;
  const headers: Record<string, string> = { 'User-Agent': 'Mozilla/5.0', Accept: 'application/json' };
  if (cfg.soundcloudOauthToken) headers.Authorization = cfg.soundcloudOauthToken;
  const res = await fetch(url, { headers });
  if (!res.ok) {
    throw new Error(`SoundCloud stream fetch failed: HTTP ${res.status} ${(await res.text()).slice(0, 200)}`);
  }
  const payload = (await res.json()) as { collection?: SoundcloudItem[] };
  const collection = payload.collection ?? [];

  const releases: MusicRelease[] = [];
  for (const item of collection) {
    const track = item.track;
    if (!track) continue;
    const artist = track.user?.username ?? 'Unknown Artist';
    const title = track.title ?? 'Unknown Track';
    const permalink = track.permalink_url ?? '';
    if (!permalink) continue;
    releases.push({
      platform: 'soundcloud',
      artist,
      track: title,
      url: permalink,
      emailId: `sc-${track.id ?? ''}`,
      from: 'soundcloud',
      emailSubject: `SoundCloud: ${title}`,
      emailDate: item.created_at ?? new Date().toISOString(),
    });
  }
  return releases;
};

/**
 * Insert new releases into the n8n data table, skipping rows that already
 * exist (matched on emailId, or platform+url when emailId is absent).
 */
export const persistMusicReleasesActivity = async (releases: MusicRelease[]): Promise<PersistResult> => {
  const cfg = loadTeknoConfig();
  if (!cfg.releasesDatabaseUrl) {
    throw new Error('Missing RELEASES_DATABASE_URL for the music release scanner');
  }
  if (releases.length === 0) return { candidates: 0, inserted: 0, skipped: 0 };

  const pool = new Pool({ connectionString: cfg.releasesDatabaseUrl, max: 2 });
  let inserted = 0;
  try {
    for (const r of releases) {
      const result = await pool.query(
        `INSERT INTO "data_table_user_GCC9783ZPWMtqQ6o"
           ("emailSubject", "emailDate", platform, url, artist, track, listened, "discoveredAt", "emailId", "from")
         SELECT $1, $2, $3, $4, $5, $6, false, $7, $8, $9
         WHERE NOT EXISTS (
           SELECT 1 FROM "data_table_user_GCC9783ZPWMtqQ6o" t
           WHERE ($8 <> '' AND t."emailId" = $8) OR (t.url = $4 AND t.platform = $3)
         )`,
        [r.emailSubject, r.emailDate, r.platform, r.url, r.artist, r.track, new Date().toISOString(), r.emailId, r.from],
      );
      if (result.rowCount && result.rowCount > 0) inserted += 1;
    }
  } catch (err) {
    // The external ReleaseS Postgres (public proxy tokaido.proxy.rlwy.net:18901) has been
    // unreachable (ECONNRESET) since ~27 Oct because its backend was removed. Persistence is
    // best-effort: do not fail the whole scan, surface the outage so the fetch still completes.
    const code = (err as { code?: string }).code;
    const detail = err instanceof Error ? err.message : String(err);
    const message = code ? `${code}: ${detail}` : detail;
    console.error(`[persistMusicReleasesActivity] ReleaseS DB unavailable, persistence skipped: ${message}`);
    return { candidates: releases.length, inserted: 0, skipped: releases.length, dbError: message };
  } finally {
    await pool.end();
  }
  return { candidates: releases.length, inserted, skipped: releases.length - inserted };
};

export const notifyMusicScanActivity = async (summary: {
  bandcamp: number;
  soundcloud: number;
  inserted: number;
  skipped: number;
  dbError?: string | undefined;
}): Promise<{ sent: boolean }> => {
  const cfg = loadTeknoConfig();
  if (!cfg.discordWebhookUrl) return { sent: false };
  const fields = [
    { name: 'Bandcamp', value: String(summary.bandcamp), inline: true },
    { name: 'SoundCloud', value: String(summary.soundcloud), inline: true },
    { name: 'New', value: String(summary.inserted), inline: true },
    { name: 'Skipped (dupes)', value: String(summary.skipped), inline: true },
  ];
  if (summary.dbError) {
    fields.push({ name: 'Persistence', value: `skipped — ${summary.dbError}`, inline: false });
  }
  const payload = {
    embeds: [
      {
        title: 'Music release scan complete',
        color: summary.dbError ? 15158332 : 3066993,
        fields,
      },
    ],
  };
  try {
    const res = await fetch(cfg.discordWebhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return { sent: res.ok };
  } catch {
    return { sent: false };
  }
};