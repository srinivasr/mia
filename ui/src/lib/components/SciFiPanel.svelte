<script lang="ts">
  export let title: string = "PANEL";
  export let fillHeight: boolean = false;
</script>

<div class="scifi-panel" class:fill-height={fillHeight}>
  <!-- Corner Brackets -->
  <div class="bracket tl"></div>
  <div class="bracket tr"></div>
  <div class="bracket bl"></div>
  <div class="bracket br"></div>

  <div class="panel-header">
    <div class="panel-header-title">{title}</div>
    <div class="panel-header-right">
      <slot name="header-right"></slot>
    </div>
  </div>
  
  <div class="panel-content">
    <slot></slot>
  </div>
</div>

<style>
  .scifi-panel {
    position: relative;
    background: rgba(3, 9, 20, 0.4);
    border: 1px solid rgba(0, 230, 255, 0.15);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    box-shadow: inset 0 0 20px rgba(0, 230, 255, 0.05);
    padding: 16px;
    width: 100%;
    display: flex;
    flex-direction: column;
    pointer-events: auto;
  }

  .scifi-panel.fill-height {
    height: 100%;
  }

  /* Thin corner brackets */
  .bracket {
    position: absolute;
    width: 8px;
    height: 8px;
    border: 2px solid var(--pri);
  }
  .bracket.tl { top: -1px; left: -1px; border-right: none; border-bottom: none; }
  .bracket.tr { top: -1px; right: -1px; border-left: none; border-bottom: none; }
  .bracket.bl { bottom: -1px; left: -1px; border-right: none; border-top: none; }
  .bracket.br { bottom: -1px; right: -1px; border-left: none; border-top: none; }

  .panel-header {
    color: var(--pri);
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    text-shadow: 0 0 8px rgba(0, 230, 255, 0.6), 0 0 16px rgba(0, 230, 255, 0.4);
  }
  
  .panel-header-title {
    flex: 1;
  }
  
  .panel-header-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .panel-content {
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .panel-content::-webkit-scrollbar {
    width: 4px;
    height: 4px;
  }

  .panel-content::-webkit-scrollbar-thumb {
    background: rgba(0, 230, 255, 0.2);
    border-radius: 2px;
  }

  .panel-content::-webkit-scrollbar-track {
    background: transparent;
  }
</style>
