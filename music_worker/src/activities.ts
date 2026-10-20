import { execFile } from 'node:child_process';
import { loadTeknoConfig } from './config.js';

// ---------------------------------------------------------------------------
// Configuration: loaded per activity via loadTeknoConfig() so .env changes
// and Railway dashboard overrides are always respected at runtime.
// ---------------------------------------------------------------------------

const HEALTH_TIMEOUT_MS = 15_000;
const DEPLOY_POLL_INTERVAL_MS = 15_000;
const DEPLOY_TIMEOUT_MS = 10 * 60_000;

interface RailwayDeployment {
  id: string;
  status: string;
  createdAt: string;
  meta?: {
    commitHash?: string;
    commitMessage?: string;
    branch?: string;
    repo?: string;
  };
}

// GraphQL API endpoint
const RAILWAY_GRAPHQL_URL = 'https://backboard.railway.app/graphql/v2';

async function railwayGraphQL(query: string, variables: Record<string, unknown>, token: string): Promise<unknown> {
  const res = await fetch(RAILWAY_GRAPHQL_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ query, variables }),
  });
  const data = await res.json() as { errors?: unknown[]; data?: unknown };
  if (!res.ok || data.errors) {
    throw new Error(`Railway GraphQL request failed (${res.status}): ${JSON.stringify(data.errors ?? data)}`);
  }
  return data.data;
}

async function railwayRedeploy(serviceId: string, token: string): Promise<boolean> {
  const query = `
    mutation Redeploy($environmentId: String!, $serviceId: String!) {
      serviceInstanceRedeploy(environmentId: $environmentId, serviceId: $serviceId)
    }
  `;
  const cfg = loadTeknoConfig();
  const data = await railwayGraphQL(query, {
    environmentId: cfg.releasesEnvironmentId,
    serviceId,
  }, token) as { serviceInstanceRedeploy: boolean };
  if (!data.serviceInstanceRedeploy) throw new Error(`Railway rejected redeploy for service ${serviceId}`);
  return data.serviceInstanceRedeploy;
}

async function railwayDeployments(limit: number, serviceId?: string): Promise<RailwayDeployment[]> {
  const cfg = loadTeknoConfig();
  if (!cfg.releasesRailwayToken) {
    throw new Error('Missing RAILWAY_RELEASES_TOKEN: set the Releases-project token as a Railway Worker variable');
  }
  
  const query = `
    query Deployments($input: DeploymentListInput!, $first: Int!) {
      deployments(input: $input, first: $first) {
        edges {
          node {
            id
            status
            createdAt
            meta
          }
        }
      }
    }
  `;
  
  const variables = {
    input: {
      projectId: cfg.releasesProjectId,
      environmentId: cfg.releasesEnvironmentId,
      serviceId: serviceId ?? cfg.stagingServiceId,
    },
    first: limit,
  };
  
  const data = await railwayGraphQL(query, variables, cfg.releasesRailwayToken) as {
    deployments: { edges: { node: RailwayDeployment }[] };
  };
  
  return data.deployments.edges.map((edge) => edge.node);
}

function runCmd(
  cmd: string,
  args: string[],
  extraEnv: Record<string, string> = {},
): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    execFile(cmd, args, { maxBuffer: 16 * 1024 * 1024, env: { ...process.env, ...extraEnv } }, (err, stdout, stderr) => {
      if (err) {
        reject(new Error(`${cmd} ${args.join(' ')} failed: ${stderr || err.message}`));
      } else {
        resolve({ stdout: String(stdout), stderr: String(stderr) });
      }
    });
  });
}

async function httpGet(
  url: string,
  timeoutMs: number,
): Promise<{ ok: boolean; status: number; ms: number; bodySnippet: string }> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  const start = Date.now();
  try {
    const res = await fetch(url, { signal: ctrl.signal, redirect: 'follow' });
    const ms = Date.now() - start;
    const text = await res.text();
    return { ok: res.ok, status: res.status, ms, bodySnippet: text.slice(0, 200) };
  } finally {
    clearTimeout(timer);
  }
}

const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms));

// ---------------------------------------------------------------------------
// Activities — every one below performs a REAL side effect or check
// ---------------------------------------------------------------------------

/**
 * Validate the release request (pure local validation — deterministic input).
 */
export const validateReleaseActivity = async (releaseRequest: {
  version: string;
  changelog: string;
  requestedBy: string;
}): Promise<{ valid: true; validatedAt: string } | { valid: false; reason: string }> => {
  if (!releaseRequest.version || !/^\d+\.\d+\.\d+$/.test(releaseRequest.version)) {
    return { valid: false, reason: 'Invalid version format. Must be semver (e.g., 1.2.3)' };
  }
  if (!releaseRequest.changelog || releaseRequest.changelog.length < 10) {
    return { valid: false, reason: 'Changelog is required and must be meaningful' };
  }
  return { valid: true, validatedAt: new Date().toISOString() };
};

/**
 * Read the latest Railway deployment for the ReleaseS service.
 * Real CI/CD read: returns the actual deployment id + commit metadata.
 */
export const buildAppActivity = async (params: {
  version: string;
  sourceCommit: string;
}): Promise<{
  buildId: string;
  artifacts: string[];
  builtAt: string;
  commit: { hash: string; message: string; branch: string; repo: string };
}> => {
  const [latest] = await railwayDeployments(1);
  if (!latest) throw new Error('No Railway deployments found for ReleaseS service');
  return {
    buildId: latest.id,
    artifacts: [
      `railway-deployment:${latest.id}`,
      `commit:${latest.meta?.commitHash ?? 'unknown'}`,
      `tekno-app-v${params.version}.zip`,
    ],
    builtAt: latest.createdAt,
    commit: {
      hash: latest.meta?.commitHash ?? 'unknown',
      message: latest.meta?.commitMessage ?? '',
      branch: latest.meta?.branch ?? '',
      repo: latest.meta?.repo ?? '',
    },
  };
};

/**
 * Real test gate: TypeScript compile check of this repo + live HTTP health
 * check against the deployed tekno app.
 */
export const runTestsActivity = async (
  buildId: string,
): Promise<{
  passed: boolean;
  testResults: { total: number; passed: number; failed: number };
  suites: { name: string; passed: boolean; detail: string }[];
  completedAt: string;
}> => {
  const suites: { name: string; passed: boolean; detail: string }[] = [];

  let typecheckPassed = false;
  let typecheckDetail = '';
  try {
    await runCmd('npx', ['tsc', '--noEmit']);
    typecheckPassed = true;
    typecheckDetail = 'tsc --noEmit clean';
  } catch (err) {
    typecheckDetail = err instanceof Error ? err.message.slice(-2000) : String(err);
  }
  suites.push({ name: `typecheck (build ${buildId})`, passed: typecheckPassed, detail: typecheckDetail });

  let healthPassed = false;
  let healthDetail = '';
  try {
    const cfg = loadTeknoConfig();
    const res = await httpGet(cfg.prodUrl, HEALTH_TIMEOUT_MS);
    healthPassed = res.ok;
    healthDetail = `GET ${cfg.prodUrl} -> ${res.status} in ${res.ms}ms`;
  } catch (err) {
    healthDetail = err instanceof Error ? err.message : String(err);
  }
  suites.push({ name: 'health: tekno prod URL', passed: healthPassed, detail: healthDetail });

  const passedCount = suites.filter((s) => s.passed).length;
  return {
    passed: passedCount === suites.length,
    testResults: { total: suites.length, passed: passedCount, failed: suites.length - passedCount },
    suites,
    completedAt: new Date().toISOString(),
  };
};

/**
 * REAL deploy: trigger `railway redeploy` for the ReleaseS service and poll
 * until the new deployment reaches a terminal healthy state.
 */
export const deployToStagingActivity = async (params: {
  buildId: string;
  version: string;
}): Promise<{ deploymentId: string; url: string; deployedAt: string }> => {
  const cfg = loadTeknoConfig();
  if (!cfg.releasesRailwayToken) {
    throw new Error('Missing RAILWAY_RELEASES_TOKEN: set the Releases-project token as a Railway Worker variable');
  }
  const triggeredAt = Date.now();
  await railwayRedeploy(cfg.stagingServiceId, cfg.releasesRailwayToken);

  const deadline = Date.now() + DEPLOY_TIMEOUT_MS;
  for (;;) {
    const deployments = await railwayDeployments(3, cfg.stagingServiceId);
    const candidate = deployments.find((d) => Date.parse(d.createdAt) >= triggeredAt - 60_000);
    if (candidate && ['SUCCESS', 'SLEEPING'].includes(candidate.status)) {
      return { deploymentId: candidate.id, url: cfg.stagingUrl, deployedAt: candidate.createdAt };
    }
    if (candidate && ['FAILED', 'CRASHED'].includes(candidate.status)) {
      throw new Error(`Staging redeploy ${candidate.id} ended with status ${candidate.status}`);
    }
    if (Date.now() > deadline) {
      throw new Error('Timed out waiting for staging redeploy to become healthy');
    }
    await sleep(DEPLOY_POLL_INTERVAL_MS);
  }
};

/**
 * REAL promote/verify: confirm the staging deployment is healthy and the
 * production URL answers. No second redeploy — promotion is verification.
 */
export const deployToProductionActivity = async (params: {
  buildId: string;
  version: string;
  stagingDeploymentId: string;
}): Promise<{
  deploymentId: string;
  url: string;
  deployedAt: string;
  verifiedDeployment: { id: string; status: string };
}> => {
  const cfg = loadTeknoConfig();
  const deadline = Date.now() + DEPLOY_TIMEOUT_MS;
  for (;;) {
    const deployments = await railwayDeployments(10, cfg.prodServiceId);
    const target = deployments.find((d) => d.id === params.stagingDeploymentId);
    if (target && ['SUCCESS', 'SLEEPING'].includes(target.status)) {
      const health = await httpGet(cfg.prodUrl, HEALTH_TIMEOUT_MS);
      if (!health.ok) throw new Error(`Prod URL unhealthy: HTTP ${health.status}`);
      return {
        deploymentId: target.id,
        url: cfg.prodUrl,
        deployedAt: new Date().toISOString(),
        verifiedDeployment: { id: target.id, status: target.status },
      };
    }
    if (target && ['FAILED', 'CRASHED'].includes(target.status)) {
      throw new Error(`Deployment ${target.id} ended with status ${target.status}; refusing to promote`);
    }
    if (Date.now() > deadline) {
      throw new Error(`Timed out waiting for deployment ${params.stagingDeploymentId} to become healthy`);
    }
    await sleep(DEPLOY_POLL_INTERVAL_MS);
  }
};

/**
 * REAL post-deployment checks: HTTP status + latency on prod (and staging).
 */
export const postDeploymentChecksActivity = async (params: {
  version: string;
  productionDeploymentId: string;
}): Promise<{
  passed: boolean;
  prod: { ok: boolean; status: number; ms: number };
  staging: { ok: boolean; status: number; ms: number };
}> => {
  const cfg = loadTeknoConfig();
  const [prod, staging] = await Promise.all([
    httpGet(cfg.prodUrl, HEALTH_TIMEOUT_MS),
    httpGet(cfg.stagingUrl, HEALTH_TIMEOUT_MS),
  ]);
  return {
    passed: prod.ok && staging.ok,
    prod: { ok: prod.ok, status: prod.status, ms: prod.ms },
    staging: { ok: staging.ok, status: staging.status, ms: staging.ms },
  };
};

/**
 * Discord notification (fire-and-forget best-effort).
 */
export const notifyStakeholdersActivity = async (params: {
  version: string;
  status: 'success' | 'failed';
  deploymentId: string;
  notifiedBy: string;
}): Promise<{ sent: boolean; messageId?: string }> => {
  const cfg = loadTeknoConfig();
  if (!cfg.discordWebhookUrl) {
    return { sent: false };
  }
  const color = params.status === 'success' ? 3066993 : 15158332; // green / red
  const payload = {
    embeds: [{
      title: `Release ${params.version} — ${params.status.toUpperCase()}`,
      color,
      fields: [
        { name: 'Deployment', value: params.deploymentId, inline: true },
        { name: 'Notified by', value: params.notifiedBy, inline: true },
        { name: 'Timestamp', value: new Date().toISOString(), inline: true },
      ],
    }],
  };
  try {
    await fetch(cfg.discordWebhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return { sent: true };
  } catch {
    return { sent: false };
  }
};