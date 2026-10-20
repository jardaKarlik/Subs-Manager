/**
 * Central environment configuration for the release list worker.
 * Fails fast on missing required vars instead of silently falling back.
 */
export interface TeknoEnvConfig {
  temporalAddress: string;
  releasesRailwayToken: string;
  releasesProjectId: string;
  releasesEnvironmentId: string;
  releasesEnv: string;
  stagingServiceId: string;
  prodServiceId: string;
  stagingUrl: string;
  prodUrl: string;
  discordWebhookUrl: string;
  composioApiKey: string;
  composioOutlookAccountId: string;
  composioUserId: string;
  soundcloudClientId: string;
  soundcloudOauthToken: string;
  releasesDatabaseUrl: string;
  bandcampLookbackDays: number;
}

function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
}

function optional(name: string, fallback: string): string {
  return process.env[name] ?? fallback;
}

/** Load and validate env config. Call once at worker/client startup. */
export function loadTeknoConfig(): TeknoEnvConfig {
  const prodUrl = optional('TEKNO_PROD_URL', 'https://tekno.up.railway.app');
  const stagingServiceId = optional(
    'RELEASES_STAGING_SERVICE_ID',
    optional('RELEASES_SERVICE_ID', '39ab8724-a7a5-4162-b585-cb7779194bf3'),
  );
  const prodServiceId = optional(
    'RELEASES_PROD_SERVICE_ID',
    optional('RELEASES_SERVICE_ID', '39ab8724-a7a5-4162-b585-cb7779194bf3'),
  );
  return {
    // TEMPORAL_ADDRESS stays optional: workers default to localhost for local dev.
    // On Railway internal network this is temporal.railway.internal:7233.
    temporalAddress: optional('TEMPORAL_ADDRESS', 'localhost:7233'),
    releasesRailwayToken: optional('RAILWAY_RELEASES_TOKEN', ''),
    releasesProjectId: optional(
      'RELEASES_PROJECT_ID',
      'ce27c333-68c0-4d53-a139-1688261d3452',
    ),
    releasesEnvironmentId: optional('RELEASES_ENVIRONMENT_ID', '399346e6-8d8d-4b00-bae0-0013b277bd96'),
    releasesEnv: optional('RELEASES_ENV', 'production'),
    stagingServiceId,
    prodServiceId,
    stagingUrl: optional('TEKNO_STAGING_URL', prodUrl),
    prodUrl,
    // Discord is intentionally optional: notifications skip safely without it.
    discordWebhookUrl: optional('DISCORD_WEBHOOK_URL', ''),
    // Music release scanner sources.
    composioApiKey: optional('COMPOSIO_API_KEY', ''),
    composioOutlookAccountId: optional('COMPOSIO_OUTLOOK_ACCOUNT_ID', 'ca_NiV5biG7fNe9'),
    composioUserId: optional('COMPOSIO_USER_ID', 'pg-test-ec47378e-e30d-4d02-b35f-8dacaa4dbf9c'),
    soundcloudClientId: optional('SOUNDCLOUD_CLIENT_ID', ''),
    soundcloudOauthToken: optional('SOUNDCLOUD_OAUTH_TOKEN', ''),
    releasesDatabaseUrl: optional('RELEASES_DATABASE_URL', ''),
    bandcampLookbackDays: Number(optional('BANDCAMP_LOOKBACK_DAYS', '7')),
  };
}

/** Hard requirement used only in Railway-deployed code paths. */
export function requireDiscordWebhook(): string {
  return required('DISCORD_WEBHOOK_URL');
}
