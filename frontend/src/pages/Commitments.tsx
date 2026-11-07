import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Badge, Card, Empty, ErrorBanner, Spinner, StatusBadge, fmtDate, useLoad } from "../components/ui";
import type { Commitment } from "../types";

const FILTERS = ["all", "pending", "completed", "overdue"] as const;
const STATUSES = ["pending", "in_progress", "completed", "cancelled"];

export default function Commitments() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const { data, error, loading, reload } = useLoad(() => api.get<Commitment[]>(`/api/commitments?filter=${filter}`), [filter]);
  const [err, setErr] = useState<unknown>(null);
  const [warn, setWarn] = useState<string | null>(null);

  const setStatus = async (c: Commitment, status: string) => {
    setErr(null); setWarn(null);
    try {
      const r = await api.patch<{ memory_synced: boolean; memory_error?: string }>(`/api/commitments/${c.id}`, { status });
      if (!r.memory_synced) setWarn(`Status saved, but Hindsight memory was NOT updated: ${r.memory_error}`);
      reload();
    } catch (e) { setErr(e); }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <h1 className="text-lg font-semibold text-slate-100">Commitment tracker</h1>
      <div className="flex gap-1">{FILTERS.map((f) => (
        <button key={f} onClick={() => setFilter(f)} className={`rounded-md border px-3 py-1.5 text-sm capitalize ${filter === f ? "border-accent bg-accent/15 text-white" : "border-ink-500 text-slate-400 hover:bg-ink-700"}`}>{f}</button>))}</div>
      <ErrorBanner error={err ?? error} />
      {warn && <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">{warn}</div>}
      <Card className="overflow-x-auto">
        {loading && !data ? <Spinner /> : !data?.length ? <Empty>No commitments in this view.</Empty> : (
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b border-ink-600 text-left text-xs text-slate-400"><tr>{["Commitment", "Responsible", "Source meeting", "Created", "Due", "Status"].map((h) => <th key={h} className="px-4 py-2 font-medium">{h}</th>)}</tr></thead>
            <tbody>{data.map((c) => (
              <tr key={c.id} className="border-b border-ink-700 last:border-0">
                <td className="px-4 py-3 text-slate-100">{c.description} {c.is_sample && <Badge tone="sample">sample</Badge>}</td>
                <td className="px-4 py-3">{c.owner_name}</td>
                <td className="px-4 py-3"><Link className="text-accent-soft" to={`/meetings/${c.meeting_id}`}>{c.meeting_title}</Link><div className="text-xs text-slate-500">{fmtDate(c.meeting_date)}</div></td>
                <td className="px-4 py-3 text-slate-400">{fmtDate(c.created_at)}</td>
                <td className="px-4 py-3 text-slate-400">{fmtDate(c.due_date)}</td>
                <td className="px-4 py-3"><div className="flex items-center gap-2"><StatusBadge status={c.status} />
                  <select className="!w-auto !py-1 text-xs" value={c.stored_status} onChange={(e) => setStatus(c, e.target.value)}>{STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}</select></div></td>
              </tr>))}</tbody>
          </table>)}
      </Card>
    </div>
  );
}
