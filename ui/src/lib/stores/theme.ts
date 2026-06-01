import { derived } from "svelte/store";
import { currentState } from "./miaState";

const stateColorMap: Record<string, string> = {
    Idle: "#4ae5ff",
    Listening: "#00ffff",
    Thinking: "#b34aff",
    Speaking: "#ffffff",
    Searching: "#00ff88",
    ExecutingTool: "#ffaa00",
    Error: "#ff3333",
};

export const stateColor = derived(currentState, ($s) =>
    stateColorMap[$s] || "#4ae5ff",
);

export function hexToRgb(hex: string) {
    const v = parseInt(hex.slice(1), 16);
    return { r: (v >> 16) & 0xff, g: (v >> 8) & 0xff, b: v & 0xff };
}

export function getStateColor(state: string): string {
    return stateColorMap[state] || "#4ae5ff";
}
