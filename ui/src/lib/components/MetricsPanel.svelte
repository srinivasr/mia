<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { invoke } from "@tauri-apps/api/core";
  import MetricBar from "./MetricBar.svelte";

  let cpu = 0;
  let mem = 0;
  let memGb = "";
  let gpu = 0;
  let vram = 0;
  let vramGb = "";
  let uptime = "--";

  let interval: ReturnType<typeof setInterval>;

  async function fetchStats() {
    try {
      const data: any = await invoke("get_system_stats");
      cpu = data.cpu_percent || 0;
      mem = data.ram_percent || 0;
      memGb = data.ram_used_gb ? `${data.ram_used_gb.toFixed(1)} GB` : "--";
      
      gpu = data.gpu_percent || 0;
      vram = data.vram_percent || 0;
      vramGb = data.vram_used_gb ? `${data.vram_used_gb.toFixed(1)} GB` : "--";

      if (data.uptime_seconds) {
          const h = Math.floor(data.uptime_seconds / 3600);
          const m = Math.floor((data.uptime_seconds % 3600) / 60);
          uptime = `${h}h ${m}m`;
      }
    } catch (e) {
      console.error("Failed to fetch system stats:", e);
    }
  }

  onMount(() => {
    fetchStats();
    interval = setInterval(fetchStats, 1500);
  });

  onDestroy(() => {
    clearInterval(interval);
  });
</script>

<div class="metrics-panel">
  <div class="header">SYSTEM METRICS</div>
  <MetricBar label="CPU" value={cpu} text="{cpu.toFixed(1)}%" color="var(--pri)" />
  <MetricBar label="MEM" value={mem} text={memGb} color="var(--pri-dim)" />
  <MetricBar label="GPU" value={gpu} text={gpu >= 0 ? `${gpu.toFixed(1)}%` : "--"} color="var(--green)" />
  <MetricBar label="VRAM" value={vram} text={vramGb} color="var(--green-d)" />
  <MetricBar label="UPTIME" value={0} text={uptime} color="var(--pri-dim)" />
</div>

<style>
  .metrics-panel {
    width: 148px; /* _LEFT_W from Python code */
    display: flex;
    flex-direction: column;
    pointer-events: auto;
  }

  .header {
    font-family: "Courier New", Courier, monospace;
    font-size: 11px;
    font-weight: bold;
    color: var(--border-b);
    margin-bottom: 8px;
    text-align: center;
    letter-spacing: 1px;
  }
</style>
