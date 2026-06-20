<!--
  DropZone — file upload target.
  When `file` prop is set, renders a compact "file selected" chip instead of the full drop area.
-->
<script lang="ts">
  let {
    limitMb = 1,
    onfile,
    onfiles,
    file = null,
    onclear,
    multiple = false,
  }: {
    limitMb?: number;
    onfile?: (file: File) => void;
    onfiles?: (files: File[]) => void;
    file?: File | null;
    onclear?: () => void;
    multiple?: boolean;
  } = $props();

  let isDragging = $state(false);
  let input = $state<HTMLInputElement>();

  const ACCEPTED = '.txt,.csv,.json,.pdf,.docx,.xlsx,.xml,.zip,.png,.jpg,.jpeg,.tiff,.bmp,.webp,.gif';

  function dispatch(files: FileList | null) {
    if (!files || files.length === 0) return;
    if (multiple && onfiles) {
      onfiles(Array.from(files));
    } else {
      onfile?.(files[0]);
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDragging = false;
    dispatch(e.dataTransfer?.files ?? null);
  }

  function handleChange(e: Event) {
    dispatch((e.target as HTMLInputElement).files);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input?.click(); }
  }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  }
</script>

<input
  bind:this={input}
  type="file"
  accept={ACCEPTED}
  multiple={multiple}
  class="visually-hidden"
  onchange={handleChange}
  aria-hidden="true"
  tabindex="-1"
/>

{#if file}
  <!-- Compact selected-file chip -->
  <div
    class="file-chip"
    class:dragging={isDragging}
    role="button"
    tabindex="0"
    aria-label="Change file — {file.name}"
    onclick={() => input?.click()}
    onkeydown={handleKeydown}
    ondragover={(e) => { e.preventDefault(); isDragging = true; }}
    ondragleave={() => (isDragging = false)}
    ondrop={handleDrop}
  >
    <div class="chip-icon" aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
        <polyline points="13 2 13 9 20 9"/>
      </svg>
    </div>
    <div class="chip-info">
      <span class="chip-name" title={file.name}>{file.name}</span>
      <span class="chip-size">{formatSize(file.size)} · click to change</span>
    </div>
    <button
      class="chip-clear"
      aria-label="Remove file"
      onclick={(e) => { e.stopPropagation(); onclear?.(); }}
    >×</button>
  </div>
{:else}
  <!-- Full drop area -->
  <div
    class="dropzone"
    class:dragging={isDragging}
    role="button"
    tabindex="0"
    aria-label="Drop file or click to select"
    onclick={() => input?.click()}
    onkeydown={handleKeydown}
    ondragover={(e) => { e.preventDefault(); isDragging = true; }}
    ondragleave={() => (isDragging = false)}
    ondrop={handleDrop}
  >
    <span class="icon" aria-hidden="true">↑</span>
    <p class="label">Drop your file here<br />or <span class="link">click to select</span></p>
    <p class="formats">.txt .csv .json .pdf .docx .xlsx .xml .zip · PNG JPG TIFF BMP WEBP GIF</p>
    <p class="limit">Max file size: {limitMb} MB</p>
  </div>
{/if}

<style>
  .dropzone {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: var(--space-3); padding: var(--space-6);
    border: 2px dashed var(--color-border); border-radius: var(--radius-lg);
    cursor: pointer; text-align: center;
    transition: border-color var(--duration-fast) var(--ease-out),
                background   var(--duration-fast) var(--ease-out);
  }
  .dropzone:hover, .dropzone:focus-visible, .dropzone.dragging {
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 6%, transparent);
    outline: none;
  }
  .icon { font-size: 2rem; color: var(--color-accent); }
  .label { margin: 0; font-size: var(--text-lg); }
  .link { color: var(--color-accent); text-decoration: underline; }
  .formats { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); font-family: var(--font-mono); }
  .limit { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); }

  /* File chip */
  .file-chip {
    display: flex; align-items: center; gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    border: 1px solid var(--color-accent);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-accent) 6%, transparent);
    cursor: pointer;
    transition: border-color var(--duration-fast), background var(--duration-fast);
  }
  .file-chip:hover, .file-chip:focus-visible, .file-chip.dragging {
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 12%, transparent);
    outline: none;
  }
  .chip-icon { color: var(--color-accent); flex-shrink: 0; display: flex; }
  .chip-info {
    flex: 1; min-width: 0;
    display: flex; flex-direction: column; gap: 2px;
  }
  .chip-name {
    font-size: var(--text-sm); font-weight: 500;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    color: var(--color-text-primary);
  }
  .chip-size {
    font-size: 0.72rem; color: var(--color-text-secondary);
    font-family: var(--font-mono);
  }
  .chip-clear {
    background: none; border: none;
    color: var(--color-text-secondary);
    font-size: 1.25rem; line-height: 1;
    cursor: pointer; padding: 2px 4px; border-radius: 4px;
    flex-shrink: 0;
    transition: color var(--duration-fast), background var(--duration-fast);
  }
  .chip-clear:hover { color: var(--color-error); background: color-mix(in srgb, var(--color-error) 10%, transparent); }
</style>
