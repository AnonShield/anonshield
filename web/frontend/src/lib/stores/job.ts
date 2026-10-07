/**
 * Active job state store.
 */
import { writable } from 'svelte/store';
import type { JobStatus } from '#lib/api.js';

export interface ActiveJob {
  id: string;
  filename: string;
  status: JobStatus | null;
  /** Stops following the job's status (watchJob). */
  stopPolling: (() => void) | null;
}

export const activeJob = writable<ActiveJob | null>(null);

export function clearJob() {
  activeJob.update(j => {
    j?.stopPolling?.();
    return null;
  });
}
