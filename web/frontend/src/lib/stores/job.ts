/**
 * Active job state store.
 */
import { writable } from 'svelte/store';
import type { JobStatus } from '$lib/api';

export interface ActiveJob {
  id: string;
  filename: string;
  status: JobStatus | null;
  pollInterval: ReturnType<typeof setInterval> | null;
}

export const activeJob = writable<ActiveJob | null>(null);

export function clearJob() {
  activeJob.update(j => {
    if (j?.pollInterval) clearInterval(j.pollInterval);
    return null;
  });
}
