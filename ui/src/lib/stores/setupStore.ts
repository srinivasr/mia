import { writable } from 'svelte/store';

export type SetupStep = 'loading' | 'api_key' | 'checks' | 'ready';

export interface CheckResult {
  mic: boolean | 'listening' | null;
  speakers: boolean | null;
  internet: boolean | null;
  gemini: boolean | null;
}

export interface CheckErrors {
  mic?: string;
  speakers?: string;
  internet?: string;
  gemini?: string;
}

export interface ConfigStatus {
  configured: boolean;
  key_valid: boolean | null;
  checks: CheckResult;
  check_errors: CheckErrors;
}

export const setupStep = writable<SetupStep>('loading');
export const apiKey = writable<string>('');
export const apiKeyError = writable<string>('');
export const configStatus = writable<ConfigStatus>({
  configured: false,
  key_valid: null,
  checks: { mic: null, speakers: null, internet: null, gemini: null },
  check_errors: {},
});
export const checkRunning = writable<string | null>(null);
export const wizardComplete = writable<boolean>(false);
