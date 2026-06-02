<script lang="ts">
  import { onMount, onDestroy, tick } from "svelte";
  import { invoke } from "@tauri-apps/api/core";
  import { currentState, latencyMs, isConnected } from "../stores/miaState";
  import { stateColor } from "../stores/theme";

  let cpu = 0;
  let mem = 0;
  let memGb = "--";
  let gpu = 0;
  let vram = 0;
  let vramGb = "--";
  let uptime = "--";
  let fetchError = "";
  let hasGpu = false;

  let cpuHistory: number[] = [];
  let memHistory: number[] = [];
  let gpuHistory: number[] = [];
  let vramHistory: number[] = [];

  let cpuSpark: HTMLCanvasElement;
  let memSpark: HTMLCanvasElement;
  let gpuSpark: HTMLCanvasElement;
  let vramSpark: HTMLCanvasElement;

  let pollInterval: ReturnType<typeof setInterval>;

  const SPARK_PTS = 40;
  const SPARK_W = 180;
  const SPARK_H = 24;

  function drawSparkline(c: HTMLCanvasElement, data: number[], color: string) {
    if (!c) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const w = c.width;
    const h = c.height;
    ctx.clearRect(0, 0, w, h);
    for (let x = 4; x < w; x += 4) {
      ctx.fillStyle = "rgba(255,255,255,0.04)";
      ctx.fillRect(x, h - 4, 1, 1);
    }
    if (data.length < 2) return;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath();
    const step = w / (SPARK_PTS - 1);
    for (let i = 0; i < data.length; i++) {
      const x = i * step;
      const y = h - (data[i] / 100) * (h - 4) - 2;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  function pushHistory(arr: number[], val: number) {
    arr.push(val);
    if (arr.length > SPARK_PTS) arr.shift();
  }

  function doBlockCount(val: number): number {
    return Math.round(Math.min(100, Math.max(0, val)) / 5);
  }

  async function fetchStats() {
    try {
      const data: any = await invoke("get_system_stats");
      fetchError = "";
      cpu = data.cpu_percent ?? 0;
      mem = data.ram_percent ?? 0;
      memGb = data.ram_used_gb != null ? `${data.ram_used_gb.toFixed(1)} GB` : "--";
      gpu = data.gpu_percent ?? 0;
      vram = data.vram_percent ?? 0;
      vramGb = data.vram_used_gb != null ? `${data.vram_used_gb.toFixed(1)} GB` : "--";
      hasGpu = data.gpu_percent != null;
      if (data.uptime_seconds) {
        const h = Math.floor(data.uptime_seconds / 3600);
        const m = Math.floor((data.uptime_seconds % 3600) / 60);
        uptime = `${h}h ${m}m`;
      }
      pushHistory(cpuHistory, cpu);
      pushHistory(memHistory, mem);
      pushHistory(gpuHistory, gpu);
      pushHistory(vramHistory, vram);
      await tick();
      drawSparkline(cpuSpark, cpuHistory, "#e8643b");
      drawSparkline(memSpark, memHistory, "#d4943a");
      drawSparkline(gpuSpark, gpuHistory, "#a85d66");
      drawSparkline(vramSpark, vramHistory, "#7a8a55");
    } catch (e: any) {
      fetchError = e?.message || String(e);
      console.error("Failed to fetch system stats:", e);
    }
  }

  $: borderRgb = (() => {
    const v = parseInt($stateColor.slice(1), 16);
    return `${(v >> 16) & 0xff}, ${(v >> 8) & 0xff}, ${v & 0xff}`;
  })();

  onMount(() => {
    fetchStats();
    pollInterval = setInterval(fetchStats, 1500);
  });

  onDestroy(() => {
    clearInterval(pollInterval);
  });
</script>

<div class="telemetry" style="border-color: rgba({borderRgb}, 0.25)">
  {#if fetchError}
    <div class="error-banner">Stats unavailable</div>
  {/if}

  <div class="section">
    <div class="section-header">SYSTEM RESOURCES</div>

    <div class="metric-row">
      <div class="metric-info">
        <span class="metric-label">CPU</span>
        <span class="metric-pct" style="color: #e8643b">{cpu.toFixed(0)}%</span>
      </div>
      <div class="metric-bar">
        {#each Array(20) as _, i}
          <div class="block" class:filled={i < doBlockCount(cpu)} style="--mc: #e8643b"></div>
        {/each}
      </div>
      <div class="metric-details">
        <span class="metric-text">{cpu.toFixed(1)}%</span>
        <canvas bind:this={cpuSpark} width={SPARK_W} height={SPARK_H} class="sparkline"></canvas>
      </div>
    </div>

    <div class="metric-row">
      <div class="metric-info">
        <span class="metric-label">RAM</span>
        <span class="metric-pct" style="color: #d4943a">{mem.toFixed(0)}%</span>
      </div>
      <div class="metric-bar">
        {#each Array(20) as _, i}
          <div class="block" class:filled={i < doBlockCount(mem)} style="--mc: #d4943a"></div>
        {/each}
      </div>
      <div class="metric-details">
        <span class="metric-text">{memGb}</span>
        <canvas bind:this={memSpark} width={SPARK_W} height={SPARK_H} class="sparkline"></canvas>
      </div>
    </div>

    {#if hasGpu}
      <div class="metric-row">
        <div class="metric-info">
          <span class="metric-label">GPU</span>
          <span class="metric-pct" style="color: #a85d66">{gpu.toFixed(0)}%</span>
        </div>
        <div class="metric-bar">
          {#each Array(20) as _, i}
            <div class="block" class:filled={i < doBlockCount(gpu)} style="--mc: #a85d66"></div>
          {/each}
        </div>
        <div class="metric-details">
          <span class="metric-text">{gpu.toFixed(1)}%</span>
          <canvas bind:this={gpuSpark} width={SPARK_W} height={SPARK_H} class="sparkline"></canvas>
        </div>
      </div>

      <div class="metric-row">
        <div class="metric-info">
          <span class="metric-label">VRAM</span>
          <span class="metric-pct" style="color: #7a8a55">{vram.toFixed(0)}%</span>
        </div>
        <div class="metric-bar">
          {#each Array(20) as _, i}
            <div class="block" class:filled={i < doBlockCount(vram)} style="--mc: #7a8a55"></div>
          {/each}
        </div>
        <div class="metric-details">
          <span class="metric-text">{vramGb}</span>
          <canvas bind:this={vramSpark} width={SPARK_W} height={SPARK_H} class="sparkline"></canvas>
        </div>
      </div>
    {/if}
  </div>

  <div class="section">
    <div class="section-header">RUNTIME</div>
    <div class="runtime-row">
      <span class="rt-label">State</span>
      <span class="rt-value" style="color: {$stateColor}">{$currentState}</span>
    </div>
    <div class="runtime-row">
      <span class="rt-label">Latency</span>
      <span
        class="rt-value"
        style="color: {$latencyMs < 50 ? 'var(--green)' : $latencyMs < 200 ? 'var(--acc2)' : 'var(--red)'}"
      >{$latencyMs}ms</span>
    </div>
    <div class="runtime-row">
      <span class="rt-label">Status</span>
      <span class="rt-value" style="color: {$isConnected ? 'var(--green)' : 'var(--red)'}">
        {$isConnected ? "ONLINE" : "OFFLINE"}
      </span>
    </div>
    <div class="runtime-row">
      <span class="rt-label">Uptime</span>
      <span class="rt-value" style="color: var(--text-dim)">{uptime}</span>
    </div>
  </div>
</div>

<style>
  .telemetry {
    background: rgba(5, 10, 21, 0.65);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid;
    border-radius: 14px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
    padding: 16px 14px;
    width: 100%;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
    pointer-events: auto;
  }

  .error-banner {
    background: rgba(255, 51, 51, 0.15);
    border: 1px solid rgba(255, 51, 51, 0.3);
    border-radius: 6px;
    padding: 6px 10px;
    margin-bottom: 10px;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
    font-size: 0.65rem;
    color: var(--red);
  }

  .section {
    margin-bottom: 16px;
  }

  .section:last-child {
    margin-bottom: 0;
  }

  .section-header {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.6rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.35);
    letter-spacing: 2.5px;
    text-transform: uppercase;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    margin-bottom: 10px;
  }

  .metric-row {
    margin-bottom: 10px;
  }

  .metric-row:last-child {
    margin-bottom: 0;
  }

  .metric-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }

  .metric-label {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.7rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.6);
    letter-spacing: 1px;
    text-transform: uppercase;
  }

  .metric-pct {
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .metric-bar {
    display: flex;
    gap: 2px;
    margin-bottom: 4px;
  }

  .block {
    width: 4px;
    height: 10px;
    border-radius: 1px;
    background: rgba(255, 255, 255, 0.06);
    flex-shrink: 0;
  }

  .block.filled {
    background: var(--mc);
  }

  .metric-details {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .metric-text {
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
    font-size: 0.65rem;
    color: rgba(255, 255, 255, 0.4);
  }

  .sparkline {
    width: 60px;
    height: 16px;
    border-radius: 1px;
  }

  .runtime-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 0;
  }

  .rt-label {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.7rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.45);
    letter-spacing: 1px;
    text-transform: uppercase;
  }

  .rt-value {
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
    font-size: 0.75rem;
    font-weight: 500;
  }
</style>
