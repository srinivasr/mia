<script lang="ts">
  export let label: string = "";
  export let value: number = 0; // 0-100
  export let text: string = "--";
  export let color: string = "var(--pri)";

  $: displayValue = Math.max(0, Math.min(100, value));
  
  // Logic from python MetricBar
  $: barColor = displayValue > 85 ? "var(--red)" : (displayValue > 65 ? "var(--acc)" : color);
</script>

<div class="metric-bar">
  <div class="info-row">
    <span class="label">{label}</span>
    <span class="text" style="color: {text !== '--' ? barColor : 'var(--text-dim)'}">{text}</span>
  </div>
  <div class="track">
    <div class="fill" style="width: {displayValue}%; background-color: {barColor}"></div>
  </div>
</div>

<style>
  .metric-bar {
    width: 100%;
    height: 38px;
    background-color: var(--panel2);
    border: 1px solid var(--border-a);
    border-radius: 4px;
    display: flex;
    flex-direction: column;
    padding: 4px 6px;
    margin-bottom: 6px;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex: 1;
  }

  .label {
    font-family: "Courier New", Courier, monospace;
    font-size: 11px;
    font-weight: bold;
    color: var(--text-dim);
  }

  .text {
    font-family: "Courier New", Courier, monospace;
    font-size: 12px;
    font-weight: bold;
  }

  .track {
    width: 100%;
    height: 4px;
    background-color: var(--bar-bg);
    border-radius: 2px;
    margin-top: 2px;
    overflow: hidden;
  }

  .fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s ease-out, background-color 0.3s ease;
  }
</style>
