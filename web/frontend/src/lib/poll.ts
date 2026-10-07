/**
 * Follows a job's status until it is done or failed. A request that fails (a
 * Wi-Fi blip, the server restarting) is retried: the job goes on on the
 * server, and giving up at the first failed request, as the page used to, lost
 * its result. It gives up after MAX_FAILURES in a row, or at once when the
 * server no longer knows the job.
 */
import { HttpError, pollStatus, type JobStatus } from '#lib/api.js';

export const POLL_EVERY_MS = 2000;
export const MAX_FAILURES = 15; // about 30 s without an answer

export type PollEnd = { status: JobStatus } | { lost: 'gone' | 'unreachable' };

/** Calls onUpdate with every status and onEnd once; returns a stop function. */
export function watchJob(jobId: string, onUpdate: (s: JobStatus) => void, onEnd: (end: PollEnd) => void,
                         everyMs = POLL_EVERY_MS): () => void {
  let failures = 0;
  let stopped = false;
  let timer: ReturnType<typeof setTimeout>;
  const finish = (end: PollEnd) => { stopped = true; onEnd(end); };
  const tick = async () => {
    if (stopped) return;
    try {
      const status = await pollStatus(jobId);
      if (stopped) return;
      failures = 0;
      onUpdate(status);
      if (status.status === 'done' || status.status === 'error') return finish({ status });
    } catch (e) {
      if (stopped) return;
      const gone = e instanceof HttpError && e.status === 404;
      if (gone || ++failures >= MAX_FAILURES) return finish({ lost: gone ? 'gone' : 'unreachable' });
    }
    // The next request only after this one ended: a slow answer never overlaps.
    timer = setTimeout(tick, everyMs);
  };
  timer = setTimeout(tick, everyMs);
  return () => { stopped = true; clearTimeout(timer); };
}
