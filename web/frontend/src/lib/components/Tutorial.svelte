<!--
  Tutorial coach marks — appears on first visit.
  5 steps: welcome → key → strategy → entities → done.
  Spotlight scrolls target into view; tooltip is always clamped within viewport.
-->
<script lang="ts">
  import { t } from '$lib/i18n';
  import { onMount } from 'svelte';

  let { onDone }: { onDone?: () => void } = $props();

  const STORAGE_KEY = 'anonshield_tutorial_done';

  const CARD_W = 320;
  const CARD_H = 230; // conservative estimate
  const MARGIN = 14;
  const PAD    = 12;

  let step    = $state(0);
  let visible = $state(false);
  let spotRect = $state<DOMRect | null>(null);
  let busy    = $state(false); // true while scrolling, prevents double-click

  const steps: Array<{
    selector?: string;
    titleKey: string;
    descKey: string;
    placement: 'center' | 'top' | 'bottom' | 'left' | 'right';
  }> = [
    {                                          titleKey: 'tut.s1.title', descKey: 'tut.s1.desc', placement: 'center'  },
    { selector: '[data-tut="key"]',            titleKey: 'tut.s2.title', descKey: 'tut.s2.desc', placement: 'bottom'  },
    { selector: '[data-tut="strategy"]',       titleKey: 'tut.s3.title', descKey: 'tut.s3.desc', placement: 'bottom'  },
    { selector: '[data-tut="entities"]',       titleKey: 'tut.s4.title', descKey: 'tut.s4.desc', placement: 'top'     },
    {                                          titleKey: 'tut.s5.title', descKey: 'tut.s5.desc', placement: 'center'  },
  ];

  const TOTAL = steps.length;

  function getRect(selector?: string): DOMRect | null {
    if (!selector) return null;
    return document.querySelector(selector)?.getBoundingClientRect() ?? null;
  }

  /** Scroll target into view, wait for animation, then update spotRect. */
  async function scrollAndUpdate(s: (typeof steps)[number]) {
    if (s.selector) {
      const el = document.querySelector(s.selector);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Wait for smooth scroll to settle — longer on taller pages
        await new Promise(r => setTimeout(r, 500));
        // Extra rAF to ensure layout is complete before measuring
        await new Promise(r => requestAnimationFrame(r));
      }
    }
    spotRect = getRect(s.selector);
  }

  async function advance() {
    if (busy) return;
    if (step < TOTAL - 1) {
      busy = true;
      step++;
      await scrollAndUpdate(steps[step]);
      busy = false;
    } else {
      finish();
    }
  }

  function finish() {
    visible = false;
    try { localStorage.setItem(STORAGE_KEY, '1'); } catch (_) {}
    onDone?.();
  }

  onMount(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY)) {
        visible = true;
        scrollAndUpdate(steps[0]);
      }
    } catch (_) {
      visible = true;
    }
  });

  /** Return CSS style string for the tooltip, always clamped to viewport. */
  function tooltipStyle(rect: DOMRect | null, placement: string): string {
    if (!rect || placement === 'center') return '';
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    let top: number | null  = null;
    let left: number | null = null;
    let bottom: number | null = null;

    switch (placement) {
      case 'bottom':
        top  = rect.bottom + MARGIN;
        left = rect.left;
        break;
      case 'top':
        bottom = vh - rect.top + MARGIN;
        left   = rect.left;
        break;
      case 'right':
        top  = rect.top;
        left = rect.right + MARGIN;
        // flip to left if not enough room
        if (left + CARD_W > vw - PAD) left = rect.left - CARD_W - MARGIN;
        break;
      case 'left':
        top  = rect.top;
        left = rect.left - CARD_W - MARGIN;
        // flip to right if not enough room
        if (left < PAD) left = rect.right + MARGIN;
        break;
    }

    // clamp horizontal
    if (left !== null) {
      left = Math.max(PAD, Math.min(left, vw - CARD_W - PAD));
    }
    // clamp vertical (top-based)
    if (top !== null) {
      top = Math.max(PAD, Math.min(top, vh - CARD_H - PAD));
    }
    // clamp bottom-anchored
    if (bottom !== null) {
      bottom = Math.max(PAD, Math.min(bottom, vh - PAD));
      // also ensure top edge is on-screen
      const impliedTop = vh - bottom - CARD_H;
      if (impliedTop < PAD) bottom = vh - CARD_H - PAD;
    }

    const parts: string[] = [];
    if (top    !== null) parts.push(`top:${top}px`);
    if (bottom !== null) parts.push(`bottom:${bottom}px`);
    if (left   !== null) parts.push(`left:${left}px`);
    return parts.join(';');
  }

  let currentStep = $derived(steps[step] ?? steps[0]);
  let isCentered  = $derived(currentStep.placement === 'center' || !spotRect);
</script>

{#if visible}
  <div class="tut-overlay" role="dialog" aria-modal="true" aria-label="Tutorial">

    <!-- Spotlight ring around target element -->
    {#if spotRect && !isCentered}
      <div
        class="spotlight"
        style="top:{spotRect.top - 6}px;left:{spotRect.left - 6}px;width:{spotRect.width + 12}px;height:{spotRect.height + 12}px"
      ></div>
    {/if}

    <!-- Tooltip bubble -->
    <div
      class="tut-card"
      class:centered={isCentered}
      style={isCentered ? '' : tooltipStyle(spotRect, currentStep.placement)}
    >
      <div class="tut-header">
        <span class="tut-step-indicator">
          {$t('tut.step', { n: step + 1, total: TOTAL })}
        </span>
        <button class="tut-skip" onclick={finish}>{$t('tut.skip')}</button>
      </div>

      <h3 class="tut-title">{$t(currentStep.titleKey as any)}</h3>
      <p class="tut-desc">{$t(currentStep.descKey as any)}</p>

      <div class="tut-footer">
        <div class="tut-dots">
          {#each steps as _, i}
            <button
              class="tut-dot"
              class:active={i === step}
              aria-label={`Go to step ${i + 1}`}
              onclick={async () => {
                if (busy) return;
                busy = true;
                step = i;
                await scrollAndUpdate(steps[i]);
                busy = false;
              }}
            ></button>
          {/each}
        </div>

        {#if step < TOTAL - 1}
          <button class="btn-tut-next" onclick={advance} disabled={busy}>
            {$t('tut.next')}
          </button>
        {:else}
          <button class="btn-tut-next btn-tut-finish" onclick={finish}>
            {$t('tut.finish')}
          </button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .tut-overlay {
    position: fixed; inset: 0; z-index: 9000;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(1px);
  }

  .spotlight {
    position: fixed;
    border-radius: 10px;
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.65);
    border: 2px solid rgba(108, 99, 255, 0.6);
    z-index: 9001;
    pointer-events: none;
    animation: spotPulse 2s ease-in-out infinite;
  }

  @keyframes spotPulse {
    0%, 100% { border-color: rgba(108, 99, 255, 0.45); }
    50%       { border-color: rgba(108, 99, 255, 1); }
  }

  .tut-card {
    position: fixed;
    z-index: 9002;
    width: 320px;
    background: #1a1d27;
    border: 1px solid #3d4268;
    border-radius: 14px;
    padding: 20px;
    box-shadow: 0 24px 48px rgba(0, 0, 0, 0.5);
  }

  /* centered (welcome / done) */
  .tut-card.centered {
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    animation: cardIn 260ms cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }
  @keyframes cardIn {
    from { transform: scale(0.88) translate(-50%, -50%); opacity: 0; }
    to   { transform: scale(1)    translate(-50%, -50%); opacity: 1; }
  }

  /* spotlight-adjacent */
  .tut-card:not(.centered) {
    animation: slideIn 220ms cubic-bezier(0.0, 0.0, 0.2, 1) both;
  }
  @keyframes slideIn {
    from { transform: translateY(8px); opacity: 0; }
    to   { transform: translateY(0);   opacity: 1; }
  }

  .tut-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 12px;
  }
  .tut-step-indicator {
    font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: #6c63ff;
  }
  .tut-skip {
    background: none; border: none;
    color: #8b90a8; font-size: 0.8rem; cursor: pointer;
    padding: 0;
    transition: color 100ms;
  }
  .tut-skip:hover { color: #e8eaf0; }

  .tut-title {
    margin: 0 0 8px; font-size: 1.05rem; font-weight: 700;
    color: #e8eaf0; line-height: 1.3;
  }
  .tut-desc {
    margin: 0 0 16px; font-size: 0.875rem;
    color: #9498b0; line-height: 1.55;
  }

  /* footer: dots + button side-by-side */
  .tut-footer {
    display: flex; align-items: center; justify-content: space-between;
    gap: 12px;
  }
  .tut-dots { display: flex; gap: 6px; }
  .tut-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #2d3148; border: none; cursor: pointer; padding: 0;
    transition: background 150ms, transform 150ms;
    flex-shrink: 0;
  }
  .tut-dot.active { background: #6c63ff; transform: scale(1.3); }

  .btn-tut-next {
    flex-shrink: 0;
    padding: 8px 18px;
    background: #6c63ff; color: #fff;
    border: none; border-radius: 8px;
    font-size: 0.875rem; font-weight: 600;
    cursor: pointer;
    transition: background 100ms, opacity 100ms;
  }
  .btn-tut-next:hover:not(:disabled) { background: #8178ff; }
  .btn-tut-next:disabled { opacity: 0.5; cursor: default; }
  .btn-tut-finish { background: #22c55e; }
  .btn-tut-finish:hover { background: #16a34a; }
</style>
