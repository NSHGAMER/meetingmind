import { AlertTriangle, Loader2, X } from "lucide-react";
import { useEffect, useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import { ApiError } from "../api";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-lg border border-ink-600 bg-ink-800/80 shadow-sm shadow-black/20 ${className}`}>{children}</div>;
}

export function CardHeader({ title, action, sub }: { title: string; action?: ReactNode; sub?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-ink-600 px-4 py-3">
      <div><h3 className="text-sm font-semibold text-slate-100">{title}</h3>{sub && <p className="text-xs text-slate-500">{sub}</p>}</div>
      {action}
    </div>
  );
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger"; busy?: boolean };
export function Button({ variant = "ghost", busy, children, className = "", ...p }: BtnProps) {
  const v = {
    primary: "bg-accent text-white hover:bg-indigo-500",
    ghost: "border border-ink-500 text-slate-200 hover:bg-ink-600",
    danger: "border border-red-500/40 text-red-300 hover:bg-red-500/10",
  }[variant];
  return (
    <button {...p} disabled={p.disabled || busy}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${v} ${className}`}>
      {busy && <Loader2 className="h-4 w-4 animate-spin" />}{children}
    </button>
  );
}

const tones: Record<string, string> = {
  pending: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  in_progress: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  completed: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  overdue: "bg-red-500/10 text-red-300 border-red-500/30",
  cancelled: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  sample: "bg-violet-500/10 text-violet-300 border-violet-500/30",
  memory: "bg-indigo-500/10 text-indigo-300 border-indigo-500/30",
  neutral: "bg-ink-600 text-slate-300 border-ink-500",
};
export function Badge({ tone = "neutral", children }: { tone?: string; children: ReactNode }) {
  return <span className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] font-medium ${tones[tone] ?? tones.neutral}`}>{children}</span>;
}
export const StatusBadge = ({ status }: { status: string }) => <Badge tone={status}>{status.replace("_", " ")}</Badge>;

export function ErrorBanner({ error }: { error: unknown }) {
  if (!error) return null;
  const e = error as ApiError;
  const hs = e.code === "hindsight_unavailable";
  return (
    <div className="flex items-start gap-2 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        {hs && <div className="font-semibold">Hindsight memory integration error</div>}
        {e.code === "llm_error" || e.code === "llm_invalid_response" ? <div className="font-semibold">LLM error</div> : null}
        <div className="break-words">{e.message ?? String(error)}</div>
      </div>
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return <div className="flex items-center gap-2 p-6 text-sm text-slate-400"><Loader2 className="h-4 w-4 animate-spin" />{label ?? "Loading…"}</div>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="p-6 text-center text-sm text-slate-500">{children}</div>;
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => { const h = (e: KeyboardEvent) => e.key === "Escape" && onClose(); window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h); }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 pt-16" onMouseDown={onClose}>
      <div className="w-full max-w-lg rounded-lg border border-ink-500 bg-ink-800 p-5" onMouseDown={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between"><h2 className="text-base font-semibold text-slate-100">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200"><X className="h-4 w-4" /></button></div>
        {children}
      </div>
    </div>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <div><label>{label}</label>{children}</div>;
}

/** Tiny data-fetch hook. */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    setLoading(true);
    fn().then((d) => live && (setData(d), setError(null))).catch((e) => live && setError(e)).finally(() => live && setLoading(false));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, error, loading, reload: () => setTick((t) => t + 1) };
}

export const fmtDate = (s?: string | null) => (s ? new Date(s).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "—");
export const fmtDateTime = (s: string) => new Date(s).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
