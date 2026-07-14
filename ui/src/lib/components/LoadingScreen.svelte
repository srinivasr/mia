<script lang="ts">
  import { onMount } from 'svelte';

  let displayText = '';
  const textToType = 'MIA KHAL';

  onMount(() => {
    let mounted = true;
    
    async function typeWriter() {
      await new Promise(r => setTimeout(r, 400));
      
      for (let i = 0; i < textToType.length; i++) {
        if (!mounted) return;
        displayText += textToType[i];
        await new Promise(r => setTimeout(r, 60 + Math.random() * 80));
      }
      
      if (!mounted) return;
      await new Promise(r => setTimeout(r, 1000));
      
      for (let i = 0; i < 5; i++) {
        if (!mounted) return;
        displayText = displayText.slice(0, -1);
        await new Promise(r => setTimeout(r, 30 + Math.random() * 20));
      }
    }
    
    typeWriter();
    return () => { mounted = false; };
  });
</script>

<div class="loading-screen">
  <div class="loader-content">
    <h1>
      {displayText}<span class="cursor"></span>
    </h1>
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



  h1 {
    font-size: 2rem;
    font-weight: 300;
    letter-spacing: 0.3em;
    margin-bottom: 8px;
    font-family: 'Courier New', monospace;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 2rem;
  }

  .cursor {
    display: inline-block;
    width: 0.5em;
    height: 1.2em;
    background-color: currentColor;
    margin-left: 4px;
    animation: blink 1s step-end infinite;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }


</style>
