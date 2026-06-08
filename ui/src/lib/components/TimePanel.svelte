<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import SciFiPanel from "./SciFiPanel.svelte";

  let timeString = "";
  let dateString = "";
  let timeZone = "";
  let interval: ReturnType<typeof setInterval>;

  function updateTime() {
    const now = new Date();
    let hours = now.getHours();
    const minutes = now.getMinutes();
    const seconds = now.getSeconds();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    
    hours = hours % 12;
    hours = hours ? hours : 12;
    
    const minutesStr = minutes < 10 ? '0' + minutes : minutes;
    const secondsStr = seconds < 10 ? '0' + seconds : seconds;
    
    timeString = `${hours}:${minutesStr}<span class="sec">:${secondsStr}</span> <span class="ampm">${ampm}</span>`;
    
    dateString = now.toDateString().toUpperCase();
    
    timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone.toUpperCase();
  }

  onMount(() => {
    updateTime();
    interval = setInterval(updateTime, 1000);
  });

  onDestroy(() => {
    clearInterval(interval);
  });
</script>

<SciFiPanel title="TIME">
  <div class="time-layout">
    <div class="value">{@html timeString}</div>
    <div class="details">
      <div class="d-row"><span class="d-label">DATE</span> <span class="d-val">{dateString}</span></div>
      <div class="d-row"><span class="d-label">ZONE</span> <span class="d-val">{timeZone}</span></div>
    </div>
  </div>
</SciFiPanel>

<style>
  .time-layout {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .value {
    font-size: 2.5rem;
    font-weight: 300;
    font-family: 'JetBrains Mono', monospace;
    color: var(--text);
  }
  :global(.sec) {
    color: var(--pri);
    font-size: 1.5rem;
  }
  :global(.ampm) {
    font-size: 1rem;
    color: var(--text-dim);
  }
  .details {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
  }
  .d-row {
    display: flex;
    justify-content: space-between;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    padding-bottom: 2px;
  }
  .d-label {
    color: var(--text-dim);
  }
  .d-val {
    color: var(--text);
  }
</style>
