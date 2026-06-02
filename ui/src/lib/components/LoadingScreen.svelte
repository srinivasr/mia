<script lang="ts">
  import { onMount } from 'svelte';

  let dots = '';

  onMount(() => {
    const interval = setInterval(() => {
      dots = dots.length >= 3 ? '' : dots + '.';
    }, 500);
    return () => clearInterval(interval);
  });
</script>

<div class="loading-screen">
  <div class="loader-content">
    <div class="orb-pulse"></div>
    <h1>INITIALIZING MIA{dots}</h1>
    <p>Establishing secure connection...</p>
  </div>
</div>

<style>
  .loading-screen {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg, #0a0a0f);
    z-index: 9999;
  }

  .loader-content {
    text-align: center;
    color: var(--pri, #4ae5ff);
  }

  .orb-pulse {
    width: 80px;
    height: 80px;
    margin: 0 auto 24px;
    border-radius: 50%;
    background: radial-gradient(circle, var(--pri-gho, rgba(74, 229, 255, 0.3)) 0%, transparent 70%);
    animation: pulse 1.5s ease-in-out infinite;
    box-shadow: 0 0 60px var(--pri-gho, rgba(74, 229, 255, 0.2));
  }

  @keyframes pulse {
    0%, 100% { transform: scale(0.8); opacity: 0.6; }
    50% { transform: scale(1.2); opacity: 1; }
  }

  h1 {
    font-size: 1.5rem;
    font-weight: 300;
    letter-spacing: 0.3em;
    margin-bottom: 8px;
    font-family: 'Courier New', monospace;
  }

  p {
    font-size: 0.85rem;
    opacity: 0.5;
    font-family: 'Courier New', monospace;
  }
</style>
