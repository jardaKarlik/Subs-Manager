import { Worker, NativeConnection } from '@temporalio/worker';
import * as activities from './activities.js';
import * as musicActivities from './musicReleaseActivities.js';
import { loadTeknoConfig } from './config.js';
import * as dotenv from 'dotenv';
import * as path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function run() {
  const cfg = loadTeknoConfig();
  const temporalAddress = cfg.temporalAddress;

  // Create a connection to the Temporal service
  const connection = await NativeConnection.connect({
    address: temporalAddress,
  });

  // Create a worker that will process tasks from the task queue
  const worker = await Worker.create({
    connection,
    taskQueue: 'release-list-task-queue',
    // Point to the directory containing workflow functions
    workflowsPath: path.resolve(__dirname, '..', 'src'),
    // Explicitly register activities
    activities: {
      validateReleaseActivity: activities.validateReleaseActivity,
      buildAppActivity: activities.buildAppActivity,
      runTestsActivity: activities.runTestsActivity,
      deployToStagingActivity: activities.deployToStagingActivity,
      deployToProductionActivity: activities.deployToProductionActivity,
      postDeploymentChecksActivity: activities.postDeploymentChecksActivity,
      notifyStakeholdersActivity: activities.notifyStakeholdersActivity,
      fetchBandcampReleasesActivity: musicActivities.fetchBandcampReleasesActivity,
      fetchSoundcloudReleasesActivity: musicActivities.fetchSoundcloudReleasesActivity,
      persistMusicReleasesActivity: musicActivities.persistMusicReleasesActivity,
      notifyMusicScanActivity: musicActivities.notifyMusicScanActivity
    },
  });

  // Listen for shutdown signals
  let shuttingDown = false;
  const shutdown = async () => {
    if (shuttingDown) return;
    shuttingDown = true;
    console.log('Shutting down worker...');
    try {
      await worker.shutdown();
    } catch (err) {
      console.error('Worker shutdown error:', err);
    }
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  // Run the worker
  await worker.run();
  console.log('Worker started successfully for Release List workflow');
}

run().catch((err) => {
  console.error('Worker failed to start:', err);
  process.exit(1);
});