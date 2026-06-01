<script lang="ts">
  let isHovering = false;
  let isDragOver = false;
  let currentFile: string | null = null;
  let dashOffset = 0;

  // Simple animation for the dash offset using requestAnimationFrame
  let animationId: number;
  function animate() {
    dashOffset = (dashOffset + 0.8) % 20;
    animationId = requestAnimationFrame(animate);
  }

  import { onMount, onDestroy } from 'svelte';
  onMount(() => {
    animate();
  });
  onDestroy(() => {
    cancelAnimationFrame(animationId);
  });

  function handleDragEnter(e: DragEvent) {
    e.preventDefault();
    isDragOver = true;
  }

  function handleDragLeave(e: DragEvent) {
    e.preventDefault();
    isDragOver = false;
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDragOver = false;
    if (e.dataTransfer && e.dataTransfer.files.length > 0) {
      currentFile = e.dataTransfer.files[0].name;
    }
  }

  function handleMouseEnter() {
    isHovering = true;
  }

  function handleMouseLeave() {
    isHovering = false;
  }

  function handleClick() {
    // In a real app, trigger a file dialog here.
    // We'll leave it as a mock for now to match visual parity.
  }

  $: bgColor = isDragOver ? "#001a24" : (isHovering ? "#001218" : "var(--panel)");
  $: borderColor = currentFile ? "rgba(0, 255, 136, 0.78)" : (isDragOver ? "rgba(0, 212, 255, 0.9)" : (isHovering ? "rgba(26, 92, 122, 0.78)" : "rgba(13, 51, 71, 0.63)"));
  $: iconColor = isHovering ? "var(--pri)" : "var(--pri-dim)";
  $: textColor = isHovering ? "var(--text)" : "var(--pri-dim)";
</script>

<div 
  class="file-drop-zone"
  style="background-color: {bgColor}; border-color: {borderColor}; stroke-dashoffset: {dashOffset}"
  on:dragenter={handleDragEnter}
  on:dragleave={handleDragLeave}
  on:dragover={(e) => e.preventDefault()}
  on:drop={handleDrop}
  on:mouseenter={handleMouseEnter}
  on:mouseleave={handleMouseLeave}
  on:click={handleClick}
  role="button"
  tabindex="0"
  on:keydown={(e) => e.key === 'Enter' && handleClick()}
>
  <div class="dash-border" style="border-color: {borderColor}; background-position: {dashOffset}px 0, 0 {dashOffset}px, {dashOffset}px 100%, 100% {dashOffset}px;"></div>

  {#if currentFile}
    <div class="content">
      <span class="icon" style="color: var(--green)">✓</span>
      <span class="file-name">{currentFile}</span>
    </div>
  {:else if isDragOver}
    <div class="content">
      <span class="icon" style="color: var(--pri)">↓</span>
      <span class="text" style="color: var(--pri)">Drop to upload</span>
    </div>
  {:else}
    <div class="content">
      <div class="plus-icon" style="border-color: {iconColor}">
        <div class="h-line" style="background-color: {iconColor}"></div>
        <div class="v-line" style="background-color: {iconColor}"></div>
      </div>
      <span class="text" style="color: {textColor}">Drop file here or Click to Browse</span>
    </div>
  {/if}
</div>

<style>
  .file-drop-zone {
    height: 100px;
    width: 100%;
    border-radius: 6px;
    position: relative;
    cursor: pointer;
    display: flex;
    justify-content: center;
    align-items: center;
    pointer-events: auto;
    transition: background-color 0.2s ease;
    padding: 6px;
    overflow: hidden;
  }

  .dash-border {
    position: absolute;
    top: 6px;
    left: 6px;
    right: 6px;
    bottom: 6px;
    border-radius: 6px;
    pointer-events: none;
    /* CSS hack for marching ants dashed border */
    background-image: 
      linear-gradient(90deg, currentColor 50%, transparent 50%),
      linear-gradient(180deg, currentColor 50%, transparent 50%),
      linear-gradient(90deg, currentColor 50%, transparent 50%),
      linear-gradient(180deg, currentColor 50%, transparent 50%);
    background-size: 20px 2px, 2px 20px, 20px 2px, 2px 20px;
    background-position: 0 0, 0 0, 0 100%, 100% 0;
    background-repeat: repeat-x, repeat-y, repeat-x, repeat-y;
  }

  .content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 2;
  }

  .plus-icon {
    width: 28px;
    height: 28px;
    position: relative;
    margin-bottom: 8px;
  }

  .h-line {
    position: absolute;
    top: 13px;
    left: 0;
    width: 28px;
    height: 2px;
  }

  .v-line {
    position: absolute;
    top: 0;
    left: 13px;
    width: 2px;
    height: 28px;
  }

  .icon {
    font-size: 24px;
    margin-bottom: 4px;
  }

  .text {
    font-family: "Courier New", Courier, monospace;
    font-size: 11px;
    text-align: center;
  }

  .file-name {
    font-family: "Courier New", Courier, monospace;
    font-size: 12px;
    font-weight: bold;
    color: var(--green);
    text-align: center;
    word-break: break-all;
    max-width: 90%;
  }
</style>
