import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MAX_FAILURES, watchJob, type PollEnd } from '#lib/poll.js';

// The server's answers, one per status request.
function serve(...answers: (object | number | 'offline')[]) {
  const queue = [...answers];
  vi.stubGlobal('fetch', vi.fn(async () => {
    const next = queue.length > 1 ? queue.shift()! : queue[0];
    if (next === 'offline') throw new TypeError('Failed to fetch');
    if (typeof next === 'number') return new Response('{}', { status: next });
    return new Response(JSON.stringify(next));
  }));
}

async function follow(everyMs = 10): Promise<{ end: PollEnd; seen: string[] }> {
  const seen: string[] = [];
  const end = await new Promise<PollEnd>((resolve) => watchJob('job', (s) => seen.push(s.status), resolve, everyMs));
  return { end, seen };
}

describe('watchJob', () => {
  beforeEach(() => vi.useRealTimers());
  afterEach(() => vi.unstubAllGlobals());

  it('reports every status and ends with the result', async () => {
    serve({ status: 'queued' }, { status: 'running', progress: 40 }, { status: 'done' });
    const { end, seen } = await follow();
    expect(seen).toEqual(['queued', 'running', 'done']);
    expect(end).toEqual({ status: { status: 'done' } });
  });

  it('rides out a few failed requests (the job goes on on the server)', async () => {
    serve({ status: 'running' }, 'offline', 503, 'offline', { status: 'done' });
    const { end } = await follow();
    expect(end).toEqual({ status: { status: 'done' } });
  });

  it('gives up after about 30 s without an answer', async () => {
    serve('offline');
    const { end } = await follow(1);
    expect(end).toEqual({ lost: 'unreachable' });
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(MAX_FAILURES);
  });

  it('gives up at once when the server no longer knows the job', async () => {
    serve({ status: 'running' }, 404);
    const { end } = await follow();
    expect(end).toEqual({ lost: 'gone' });
  });

  it('ends with the failure message of a failed job', async () => {
    serve({ status: 'error', message: 'Invalid JSON in report.json' });
    expect((await follow()).end).toEqual({ status: { status: 'error', message: 'Invalid JSON in report.json' } });
  });

  it('stops for good when stopped (Cancel), even with a request in flight', async () => {
    let answer!: (r: Response) => void;
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((r) => { answer = r; })));
    const onUpdate = vi.fn(), onEnd = vi.fn();
    const stop = watchJob('job', onUpdate, onEnd, 1);
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    stop();
    answer(new Response('{}', { status: 404 }));
    await new Promise((r) => setTimeout(r, 20));
    expect(onUpdate).not.toHaveBeenCalled();
    expect(onEnd).not.toHaveBeenCalled();
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
