// Cookie-less usage counts via GoatCounter, only when the build sets
// VITE_GOATCOUNTER (the GitHub Pages workflow does; local runs send nothing).
// Page loads are counted by count.js itself; feature runs are events.

const CODE = import.meta.env.VITE_GOATCOUNTER as string | undefined;
export const ANALYTICS = Boolean(CODE);
export const DASHBOARD = `https://${CODE}.goatcounter.com`;

declare global {
  interface Window {
    goatcounter?: {
      count: (o: { path: string; title?: string; event?: boolean }) => void;
    };
  }
}

export function loadAnalytics(): void {
  if (!CODE) return;
  const s = document.createElement("script");
  s.async = true;
  s.src = "https://gc.zgo.at/count.js";
  s.dataset.goatcounter = `${DASHBOARD}/count`;
  document.head.appendChild(s);
}

export function track(path: string, title?: string): void {
  window.goatcounter?.count({ path, title, event: true });
}

export class CounterError extends Error {
  constructor(readonly status: number) {
    super(`GoatCounter responded ${status}`);
  }
}

// Public counter: `count` is a formatted string ("1,234"); 404 means never hit.
// `start` is a date or `week` / `month` / `year`. Responses are cached ~4h.
export async function counter(path: string, start?: string): Promise<number> {
  const qs = start ? `?start=${start}` : "";
  const res = await fetch(`${DASHBOARD}/counter/${encodeURIComponent(path)}.json${qs}`);
  if (res.status === 404) return 0;
  if (!res.ok) throw new CounterError(res.status);
  const json = (await res.json()) as { count: string };
  return Number(json.count.replace(/\D/g, "")) || 0;
}
