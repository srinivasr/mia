<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  export let state: string = "INITIALISING";

  let blink = true;
  let tick = 0;
  let interval: ReturnType<typeof setInterval>;
  let waveformHeights = [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3];

  onMount(() => {
    interval = setInterval(() => {
      tick++;
      if (tick % 38 === 0) {
        blink = !blink;
      }
      
      // Update waveform
      const newHeights = [];
      for (let i = 0; i < 36; i++) {
        if (state === "Error") {
          newHeights.push(2);
        } else {
          newHeights.push(Math.floor(3 + 2 * Math.sin(tick * 0.09 + i * 0.6)));
        }
      }
      waveformHeights = newHeights;
    }, 16);
  });

  onDestroy(() => {
    clearInterval(interval);
  });

  $: isSpeaking = state === "Speaking";
  $: isError = state === "Error";
  $: isThinking = state === "Thinking";
  $: isListening = state === "Listening";

  $: symbol = isThinking ? (blink ? "◈" : "◇") :
             (state === "Processing" ? (blink ? "▷" : "") :
             (blink ? "●" : "○"));

  $: textColor = isError ? "var(--muted-c)" :
                (isSpeaking ? "var(--acc)" :
                ((isThinking || state === "Processing") ? "var(--acc2)" :
                (isListening ? "var(--green)" : "var(--pri)")));

  $: textStr = `${symbol}  ${state.toUpperCase()}`;

</script>

<div class="status-container">
  <div class="status-text" style="color: {textColor}">
    {textStr}
  </div>
  <div class="waveform">
    {#each waveformHeights as h}
      <div 
        class="wave-bar" 
        style="height: {h}px; background-color: {isError ? 'var(--muted-c)' : (isSpeaking ? (h > 12 ? 'var(--pri)' : 'var(--pri-dim)') : 'var(--border-b)')}"
      ></div>
    {/each}
  </div>
</div>

<style>
  .status-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin-top: auto;
    margin-bottom: 40px;
    height: 80px;
  }

  .status-text {
    font-family: "Courier New", Courier, monospace;
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 1px;
    margin-bottom: 20px;
  }

  .waveform {
    display: flex;
    align-items: flex-end;
    justify-content: center;
    height: 20px;
    gap: 7px;
  }

  .wave-bar {
    width: 7px;
    min-height: 2px;
  }
</style>
