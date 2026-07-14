<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import SciFiPanel from "./SciFiPanel.svelte";

  let timeString = "";
  let dateString = "";
  let timeZone = "";
  let userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  let interval: ReturnType<typeof setInterval>;

  async function fetchTimeZone() {
    try {
      const res = await fetch("http://ip-api.com/json/");
      const data = await res.json();
      if (data.timezone) {
        userTimeZone = data.timezone;
        updateTime();
      }
    } catch (e) {
      console.warn("Failed to fetch timezone via IP, falling back to system TZ", e);
    }
  }

  function updateTime() {
    const now = new Date();
    const timeOpts: Intl.DateTimeFormatOptions = { timeZone: userTimeZone, hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true };
    const dateOpts: Intl.DateTimeFormatOptions = { timeZone: userTimeZone, weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
    
    let timeStrRaw = new Intl.DateTimeFormat('en-US', timeOpts).format(now);
    const match = timeStrRaw.match(/^(\d{1,2}:\d{2}):(\d{2})\s*(AM|PM)$/i);
    
    if (match) {
       const [_, hm, s, ap] = match;
       timeString = `${hm}<span class="sec">:${s}</span> <span class="ampm">${ap.toUpperCase()}</span>`;
    } else {
       timeString = timeStrRaw;
    }
    
    dateString = new Intl.DateTimeFormat('en-US', dateOpts).format(now).replace(/,/g, '').toUpperCase();
    timeZone = userTimeZone.toUpperCase();
  }

  onMount(() => {
    fetchTimeZone();
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
