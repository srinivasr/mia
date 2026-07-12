<script lang="ts">
  import SciFiPanel from "./SciFiPanel.svelte";
  import { onMount, onDestroy } from "svelte";
  import { cameraFrame } from "../stores/miaState";

  let canvasElement: HTMLCanvasElement;
  let animId: number;

  $: hasError = !$cameraFrame;
  $: errorMessage = "FEED UNAVAILABLE";

  let fps = 0;
  let frames = 0;

  $: if ($cameraFrame) frames++;

  function startSimulatedFeed() {
    if (!canvasElement) return;
    const ctx = canvasElement.getContext('2d');
    if (!ctx) return;
    
    let width = canvasElement.width = 320;
    let height = canvasElement.height = 180;
    
    function draw() {
      if (!ctx) return;
      ctx.fillStyle = 'rgba(1, 4, 10, 0.2)';
      ctx.fillRect(0, 0, width, height);
      
      for(let i = 0; i < 30; i++) {
        let x = Math.random() * width;
        let y = Math.random() * height;
        let c = Math.random() > 0.9 ? '#ff4785' : '#00e6ff';
        ctx.fillStyle = c;
        ctx.globalAlpha = Math.random() * 0.5;
        ctx.fillRect(x, y, Math.random() * 2 + 1, Math.random() * 10 + 5);
      }
      ctx.globalAlpha = 1.0;
      
      let scanY = (Date.now() / 20) % height;
      ctx.fillStyle = 'rgba(0, 230, 255, 0.3)';
      ctx.fillRect(0, scanY, width, 2);
      
      animId = requestAnimationFrame(draw);
    }
    draw();
  }

  onMount(() => {
    startSimulatedFeed();
    const interval = setInterval(() => {
      fps = frames;
      frames = 0;
    }, 1000);
    
    return () => clearInterval(interval);
  });

  onDestroy(() => {
    if (animId) cancelAnimationFrame(animId);
  });
</script>

<SciFiPanel title="CAMERA FEED">
  <svelte:fragment slot="header-right">
    {#if hasError}
      <span class="err-dot"></span> <span class="err-text">OFFLINE</span>
    {:else}
      <span class="live-dot"></span> LIVE
    {/if}
  </svelte:fragment>

  <div class="camera-container">
    {#if hasError}
      <canvas bind:this={canvasElement} class="camera-feed"></canvas>
      <div class="error-overlay">
        <div class="err-msg">[{errorMessage}]</div>
        <div class="err-sub">SIMULATING FEED...</div>
      </div>
    {/if}
    <img src={$cameraFrame} class="camera-feed" class:hidden={hasError} alt="camera" />
    <div class="tracking-overlay"></div>
  </div>

  <div class="meta-bar">
    <span>VISION: <span class={hasError ? "red" : "green"}>{hasError ? "OFFLINE" : "ONLINE"}</span></span>
    <span>FPS: {hasError ? "00" : fps.toString().padStart(2, '0')}</span>
  </div>
</SciFiPanel>

<style>
  .camera-container {
    position: relative;
    width: 100%;
    aspect-ratio: 16/9;
    background: #01040a;
    overflow: hidden;
    border: 1px solid rgba(0, 230, 255, 0.2);
    border-radius: 2px;
  }
  
  .camera-feed {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transform: scaleX(-1);
  }
  
  .tracking-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    pointer-events: none;
    box-shadow: inset 0 0 40px rgba(0, 0, 0, 0.8);
  }
  

  .meta-bar {
    display: flex;
    justify-content: space-between;
    margin-top: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-dim);
    letter-spacing: 1px;
  }
  
  .green {
    color: var(--green);
  }
  
  .live-dot {
    display: inline-block;
    width: 6px; height: 6px;
    background: var(--green);
    border-radius: 50%;
    margin-right: 4px;
    box-shadow: 0 0 6px var(--green);
    animation: blink 2s infinite;
  }
  
  .err-dot {
    display: inline-block;
    width: 6px; height: 6px;
    background: var(--red);
    border-radius: 50%;
    margin-right: 4px;
    box-shadow: 0 0 6px var(--red);
  }

  .err-text {
    color: var(--red);
  }

  .red {
    color: var(--red);
  }

  .hidden {
    display: none;
  }

  .error-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: repeating-linear-gradient(
      0deg,
      rgba(0, 0, 0, 0.8),
      rgba(0, 0, 0, 0.8) 2px,
      rgba(255, 50, 50, 0.05) 2px,
      rgba(255, 50, 50, 0.05) 4px
    );
    z-index: 1;
    color: var(--red);
    font-family: 'JetBrains Mono', monospace;
    text-shadow: 0 0 8px rgba(255, 50, 50, 0.8);
  }

  .err-msg {
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 2px;
    margin-bottom: 8px;
    animation: glitch 3s infinite;
  }

  .err-sub {
    font-size: 0.65rem;
    opacity: 0.7;
    letter-spacing: 1px;
  }


  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  @keyframes glitch {
    0%, 95% { transform: translate(0); opacity: 1; }
    96% { transform: translate(-2px, 1px); opacity: 0.8; }
    97% { transform: translate(2px, -1px); opacity: 0.9; }
    98% { transform: translate(-1px, -1px); opacity: 0.8; }
    99% { transform: translate(1px, 1px); opacity: 0.9; }
    100% { transform: translate(0); opacity: 1; }
  }
</style>
