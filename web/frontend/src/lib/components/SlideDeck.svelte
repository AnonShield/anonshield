<script lang="ts">
  import { t } from '$lib/i18n';

  let { count = 30, base = '/slides', pdf = '' }: { count?: number; base?: string; pdf?: string } = $props();

  let i = $state(0);
  let stage: HTMLDivElement;
  let strip: HTMLDivElement;

  const pad = (n: number) => String(n + 1).padStart(2, '0');
  const src = (n: number) => `${base}/${pad(n)}.webp`;
  const go = (n: number) => { i = Math.max(0, Math.min(count - 1, n)); };
  const prev = () => go(i - 1);
  const next = () => go(i + 1);

  function toggleFs() {
    if (typeof document === 'undefined') return;
    if (!document.fullscreenElement) stage?.requestFullscreen?.();
    else document.exitFullscreen?.();
  }

  function onKey(e: KeyboardEvent) {
    const tag = (e.target as HTMLElement | null)?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    switch (e.key) {
      case 'ArrowRight': case 'PageDown': case ' ': e.preventDefault(); next(); break;
      case 'ArrowLeft':  case 'PageUp':            e.preventDefault(); prev(); break;
      case 'Home': e.preventDefault(); go(0); break;
      case 'End':  e.preventDefault(); go(count - 1); break;
      case 'f': case 'F': toggleFs(); break;
    }
  }

  // Preload neighbors for instant, jank-free swaps.
  $effect(() => {
    for (const n of [i + 1, i - 1]) {
      if (n >= 0 && n < count) { const im = new Image(); im.src = src(n); }
    }
  });

  // Keep the active thumbnail visible.
  $effect(() => {
    const el = strip?.querySelector(`[data-idx="${i}"]`) as HTMLElement | null;
    el?.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' });
  });
</script>

<svelte:window onkeydown={onKey} />

<div class="deck">
  <div class="stage" bind:this={stage}>
    <img class="slide" src={src(i)} alt={`${$t('slides.title')} ${i + 1}/${count}`} draggable="false" />
    <button class="edge left"  onclick={prev} disabled={i === 0}           aria-label={$t('slides.prev')}>‹</button>
    <button class="edge right" onclick={next} disabled={i === count - 1}   aria-label={$t('slides.next')}>›</button>
  </div>

  <div class="progress" aria-hidden="true"><span style={`width:${((i + 1) / count) * 100}%`}></span></div>

  <div class="bar">
    <div class="group">
      <button class="ctl" onclick={prev} disabled={i === 0}         aria-label={$t('slides.prev')}>←</button>
      <span class="counter" aria-live="polite">{i + 1} {$t('slides.of')} {count}</span>
      <button class="ctl" onclick={next} disabled={i === count - 1} aria-label={$t('slides.next')}>→</button>
    </div>
    <div class="group">
      {#if pdf}
        <a class="ctl" href={pdf} download>↓ {$t('slides.download')}</a>
      {/if}
      <button class="ctl" onclick={toggleFs} aria-label={$t('slides.fullscreen')}>⤢ {$t('slides.fullscreen')}</button>
    </div>
  </div>

  <div class="thumbs" bind:this={strip} role="tablist" aria-label={$t('slides.thumbs')}>
    {#each Array(count) as _, n (n)}
      <button
        class="thumb" class:active={n === i} data-idx={n}
        role="tab" aria-selected={n === i} aria-label={`${n + 1}`}
        onclick={() => go(n)}
      >
        <img src={src(n)} alt="" loading="lazy" draggable="false" />
      </button>
    {/each}
  </div>
</div>

<style>
  .deck { display: flex; flex-direction: column; gap: var(--space-3); }

  .stage {
    position: relative;
    aspect-ratio: 16 / 9;
    background: var(--color-surface-raised);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    overflow: hidden;
  }
  .slide {
    width: 100%; height: 100%;
    object-fit: contain;
    display: block;
    user-select: none;
  }
  /* Fullscreen keeps the slide centered on a solid backdrop. */
  .stage:fullscreen { background: #000; border: none; border-radius: 0; }
  .stage:fullscreen .slide { object-fit: contain; }

  .edge {
    position: absolute; top: 0; bottom: 0;
    width: 14%; min-width: 44px;
    display: grid; place-items: center;
    border: none; background: transparent;
    color: var(--color-text-primary);
    font-size: var(--text-2xl); line-height: 1;
    opacity: 0; cursor: pointer;
    transition: opacity var(--duration-normal) var(--ease-out),
                background var(--duration-normal) var(--ease-out);
  }
  .edge.left  { left: 0;  justify-content: flex-start; padding-left: var(--space-3); }
  .edge.right { right: 0; justify-content: flex-end;   padding-right: var(--space-3); }
  .stage:hover .edge { opacity: 0.85; }
  .edge:hover { background: color-mix(in srgb, var(--color-surface) 55%, transparent); opacity: 1; }
  .edge:focus-visible { opacity: 1; outline: 2px solid var(--color-accent); outline-offset: -4px; }
  .edge:disabled { opacity: 0 !important; pointer-events: none; }

  .progress { height: 3px; background: var(--color-border); border-radius: 999px; overflow: hidden; }
  .progress span {
    display: block; height: 100%;
    background: var(--color-accent);
    transition: width var(--duration-normal) var(--ease-out);
  }

  .bar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); flex-wrap: wrap; }
  .group { display: flex; align-items: center; gap: var(--space-2); }
  .counter {
    min-width: 5ch; text-align: center;
    font-family: var(--font-mono); font-size: var(--text-sm);
    color: var(--color-text-secondary);
  }
  .ctl {
    display: inline-flex; align-items: center; gap: var(--space-1);
    padding: var(--space-2) var(--space-3);
    background: var(--color-surface-elevated);
    border: 1px solid var(--color-border); border-radius: var(--radius-sm);
    color: var(--color-text-secondary);
    font-size: var(--text-sm); text-decoration: none;
    transition: border-color var(--duration-fast) var(--ease-out),
                color var(--duration-fast) var(--ease-out);
  }
  .ctl:hover { border-color: var(--color-accent); color: var(--color-text-primary); }
  .ctl:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
  .ctl:disabled { opacity: 0.4; pointer-events: none; }

  .thumbs {
    display: flex; gap: var(--space-2);
    overflow-x: auto; padding: var(--space-1) 0 var(--space-2);
    scrollbar-width: thin;
  }
  .thumb {
    flex: 0 0 auto;
    width: 108px; aspect-ratio: 16 / 9;
    padding: 0; border: 1px solid var(--color-border); border-radius: var(--radius-sm);
    background: var(--color-surface-raised); overflow: hidden; cursor: pointer;
    opacity: 0.55;
    transition: opacity var(--duration-fast) var(--ease-out),
                border-color var(--duration-fast) var(--ease-out),
                transform var(--duration-fast) var(--ease-out);
  }
  .thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .thumb:hover { opacity: 0.85; }
  .thumb.active { opacity: 1; border-color: var(--color-accent); transform: translateY(-2px); }
  .thumb:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; opacity: 1; }

  @media (prefers-reduced-motion: reduce) {
    .progress span, .edge, .thumb { transition: none; }
  }
  @media (max-width: 560px) {
    .thumb { width: 84px; }
  }
</style>
