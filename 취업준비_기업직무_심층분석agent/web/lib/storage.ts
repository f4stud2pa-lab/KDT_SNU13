import type { RunState } from "./pipeline";

const RUN_KEY = "jobprep.run.v1";
const KEY_KEY = "jobprep.apiKey";
const SETTINGS_KEY = "jobprep.settings.v1";

export type Settings = { model: string; effort: string };

function read<T>(key: string): T | null {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function loadRun(): RunState | null {
  const run = read<RunState>(RUN_KEY);
  return run?.version === 1 ? run : null;
}

export function saveRun(run: RunState | null) {
  try {
    if (run) window.localStorage.setItem(RUN_KEY, JSON.stringify(run));
    else window.localStorage.removeItem(RUN_KEY);
  } catch {
    // Storage full or disabled: the run continues in memory only.
  }
}

export function loadApiKey(): string {
  try {
    return window.localStorage.getItem(KEY_KEY) ?? "";
  } catch {
    return "";
  }
}

export function saveApiKey(key: string) {
  try {
    if (key) window.localStorage.setItem(KEY_KEY, key);
    else window.localStorage.removeItem(KEY_KEY);
  } catch {}
}

export function loadSettings(): Settings | null {
  return read<Settings>(SETTINGS_KEY);
}

export function saveSettings(settings: Settings) {
  try {
    window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {}
}
