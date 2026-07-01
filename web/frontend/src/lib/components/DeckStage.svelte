<script lang="ts">
  import { locale } from '$lib/i18n';
  import { EN } from '$lib/deck-en';
  import type { Slide, El, Run } from '$lib/deck';

  // `video`: quando presente, a imagem full-bleed vira <video> (slides 2/3/4).
  let { slide, video = '' }: { slide: Slide; video?: string } = $props();

  const isFull = (e: El) => e.x < 5 && e.y < 5 && e.w > 95 && e.h > 95;
  // EN vem de deck-en.ts (dicionario PT->EN); fallback para PT (codigo/numeros).
  const runText = (r: Run) => ($locale === 'en' ? EN[r.pt] ?? r.pt : r.pt);

  const fontFamily = (f?: string) =>
    f === 'head' ? 'var(--df-head)' : f === 'mono' ? 'var(--df-mono)' : 'var(--df-sans)';

  const justify = (a?: string) =>
    a === 'center' ? 'center' : a === 'end' ? 'flex-end' : 'flex-start';

  const CLIP: Record<string, string> = {
    arrow: 'polygon(0% 28%, 64% 28%, 64% 0%, 100% 50%, 64% 100%, 64% 72%, 0% 72%)',
    tri: 'polygon(50% 0%, 100% 100%, 0% 100%)',
  };
</script>

<div class="stage">
  {#each slide.els as el (el)}
    {#if el.kind === 'img'}
      {#if video && isFull(el)}
        <video
          class="el vid"
          style={`left:${el.x}%;top:${el.y}%;width:${el.w}%;height:${el.h}%`}
          src={video} poster={el.src}
          autoplay loop muted playsinline
        ></video>
      {:else}
        <img
          class="el img"
          style={`left:${el.x}%;top:${el.y}%;width:${el.w}%;height:${el.h}%`}
          src={el.src} alt="" draggable="false" loading="lazy"
        />
      {/if}
    {:else if el.kind === 'shape'}
      <div
        class="el shape"
        style={`
          left:${el.x}%;top:${el.y}%;width:${el.w}%;height:${el.h}%;
          background:${el.fill ?? 'transparent'};
          ${el.bw ? `border:max(1px, ${el.bw}cqw) solid ${el.bc};` : ''}
          border-radius:${el.sub === 'oval' ? '50%' : `${el.rx ?? 0}cqw`};
          ${el.sub === 'arrow' || el.sub === 'tri' ? `clip-path:${CLIP[el.sub]};` : ''}
          ${el.paras ? `justify-content:${justify(el.anchor)};` : ''}
        `}
      >
        {#if el.paras}
          {#each el.paras as p}
            <p class="line" style={`text-align:${p.a}`}>
              {#each p.runs as r}<span
                style={`font-family:${fontFamily(r.f)};font-size:${r.s}cqw;font-weight:${r.b ? 700 : 400};${r.c ? `color:${r.c};` : ''}`}
              >{runText(r)}</span>{/each}
            </p>
          {/each}
        {/if}
      </div>
    {:else if el.kind === 'text'}
      <div
        class="el text"
        style={`
          left:${el.x}%;top:${el.y}%;width:${el.w}%;height:${el.h}%;
          justify-content:${justify(el.anchor)};
          padding:${el.mt ?? 0}cqw ${el.ml ?? 0}cqw;
        `}
      >
        {#each el.paras ?? [] as p}
          <p class="line" style={`text-align:${p.a}`}>
            {#each p.runs as r}<span
              style={`font-family:${fontFamily(r.f)};font-size:${r.s}cqw;font-weight:${r.b ? 700 : 400};${r.c ? `color:${r.c};` : ''}`}
            >{runText(r)}</span>{/each}
          </p>
        {/each}
      </div>
    {/if}
  {/each}
</div>

<style>
  .stage {
    position: relative;
    container-type: inline-size;
    aspect-ratio: 16 / 9;
    width: 100%;
    background: #ffffff;
    overflow: hidden;
    /* fontes do deck */
    --df-head: 'Space Grotesk', 'Inter', system-ui, sans-serif;
    --df-sans: 'Inter', system-ui, sans-serif;
    --df-mono: 'JetBrains Mono', ui-monospace, monospace;
    color: #110e09;
  }
  .el { position: absolute; box-sizing: border-box; }
  .img, .vid { object-fit: contain; }
  .vid { object-fit: cover; }
  .text, .shape { display: flex; flex-direction: column; }
  .line {
    margin: 0;
    line-height: 1.18;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .line span { letter-spacing: -0.005em; }
</style>
