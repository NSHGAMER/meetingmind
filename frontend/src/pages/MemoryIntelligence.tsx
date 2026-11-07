import { Brain, DatabaseZap } from "lucide-react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { Badge, Card, CardHeader, Empty, ErrorBanner, Spinner, StatusBadge, fmtDate, fmtDateTime, useLoad } from "../components/ui";
import type { Commitment } from "../types";

interface Overview {
  meeting_interactions: number; retain_operations: number; recall_operations: number; facts_recalled_total: number; failed_operations: number;
  unresolved_commitments: Commitment[]; frequent_topics: { topic: string; count: number }[];
  contact_summaries: { contact_id: number; name: string; organization?: string; meetings: number; open_commitments: number; last_interaction: string; latest_concern: string | null }[];
  timeline: { id: number; kind: string; success: boolean; detail: string; count: number; meeting_id: number | null; created_at: string }[];
  briefing_traces: { briefing_id: number; meeting_id: number; title: string; mode: string; created_at: string; memories_retrieved: number; memories: { ref: string; text: string; source_meeting: { title: string; date: string } | null }[] }[];
}

export default function MemoryIntelligence() {
  const { data: o, error, loading } = useLoad(() => api.get<Overview>("/api/memory/overview"));
  if (loading && !o) return <Spinner />;
  if (!o) return <ErrorBanner error={error} />;
  const stats: [string, number, string][] = [
    ["Meeting interactions in memory", o.meeting_interactions, "confirmed meetings"],
    ["Facts recalled (total)", o.facts_recalled_total, `${o.recall_operations} Hindsight recall calls`],
    ["Memory writes", o.retain_operations, "Hindsight retain calls"],
    ["Unresolved commitments", o.unresolved_commitments.length, "from tracker"],
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div><h1 className="text-lg font-semibold text-slate-100">Memory Intelligence</h1>
        <p className="text-xs text-slate-500">Every number below is computed from logged Hindsight operations and stored records — none are estimated.</p></div>
      {o.failed_operations > 0 && <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{o.failed_operations} Hindsight operation(s) failed — see the timeline.</div>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{stats.map(([l, v, s]) => <Card key={l} className="p-4"><div className="text-xs text-slate-400">{l}</div><div className="mt-1 text-2xl font-semibold text-slate-100">{v}</div><div className="text-[11px] text-slate-500">{s}</div></Card>)}</div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card><CardHeader title="Frequently discussed topics" />
          {o.frequent_topics.length === 0 ? <Empty>No topics yet.</Empty> : (
            <div className="h-56 p-3"><ResponsiveContainer width="100%" height="100%"><BarChart data={o.frequent_topics} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid stroke="#1e2a45" horizontal={false} /><XAxis type="number" allowDecimals={false} stroke="#64748b" fontSize={11} /><YAxis type="category" dataKey="topic" width={120} stroke="#94a3b8" fontSize={11} />
              <Tooltip contentStyle={{ background: "#101829", border: "1px solid #2a3858", fontSize: 12 }} cursor={{ fill: "#1e2a45" }} /><Bar dataKey="count" fill="#6366f1" radius={[0, 3, 3, 0]} /></BarChart></ResponsiveContainer></div>)}
        </Card>
        <Card><CardHeader title="Important unresolved commitments" />
          {o.unresolved_commitments.length === 0 ? <Empty>Nothing unresolved.</Empty> : o.unresolved_commitments.slice(0, 6).map((c) => (
            <div key={c.id} className="flex items-center justify-between border-b border-ink-700 px-4 py-2.5 text-sm last:border-0"><span>{c.owner_name}: {c.description}<div className="text-xs text-slate-500">Due {fmtDate(c.due_date)} · {c.meeting_title}</div></span><StatusBadge status={c.status} /></div>))}
        </Card>
      </div>

      <Card><CardHeader title="Contact memory summaries" />
        {o.contact_summaries.length === 0 ? <Empty>No contact has confirmed meeting history yet.</Empty> : o.contact_summaries.map((c) => (
          <Link key={c.contact_id} to={`/contacts/${c.contact_id}`} className="block border-b border-ink-700 px-4 py-3 text-sm last:border-0 hover:bg-ink-700/40">
            <div className="flex items-center justify-between"><span className="text-slate-100">{c.name} <span className="text-xs text-slate-500">{c.organization}</span></span><span className="text-xs text-slate-500">last interaction {fmtDate(c.last_interaction)}</span></div>
            <div className="text-xs text-slate-400">{c.meetings} meeting(s) · {c.open_commitments} open commitment(s){c.latest_concern ? ` · latest concern: ${c.latest_concern}` : ""}</div></Link>))}
      </Card>

      <Card><CardHeader title="Memories retrieved for briefings" sub="Which Hindsight facts each briefing was built from" />
        {o.briefing_traces.length === 0 ? <Empty>No briefings generated yet.</Empty> : o.briefing_traces.map((b) => (
          <details key={b.briefing_id} className="border-b border-ink-700 px-4 py-3 text-sm last:border-0">
            <summary className="flex cursor-pointer items-center justify-between"><span>{b.title} <span className="text-xs text-slate-500">{fmtDateTime(b.created_at)}</span></span>
              {b.mode === "memory" ? <Badge tone="memory"><DatabaseZap className="h-3 w-3" />{b.memories_retrieved} facts retrieved</Badge> : <Badge>generic · no recall</Badge>}</summary>
            <ul className="mt-2 space-y-1 text-xs text-slate-300">{b.memories.map((m) => <li key={m.ref} className="rounded bg-ink-700/50 px-2 py-1"><b className="text-indigo-300">{m.ref}</b> {m.text}{m.source_meeting && <span className="text-slate-500"> — {m.source_meeting.title}, {fmtDate(m.source_meeting.date)}</span>}</li>)}</ul>
          </details>))}
      </Card>

      <Card><CardHeader title="Memory activity timeline" />
        {o.timeline.length === 0 ? <Empty>No memory activity yet. Confirm meeting notes or prepare a meeting.</Empty> : <ol className="space-y-2 p-4">{o.timeline.map((e) => (
          <li key={e.id} className="flex items-start gap-3 text-sm"><Brain className={`mt-0.5 h-4 w-4 shrink-0 ${e.success ? (e.kind === "retain" ? "text-emerald-400" : "text-indigo-400") : "text-red-400"}`} />
            <div><div className={e.success ? "text-slate-200" : "text-red-300"}>{e.detail}</div><div className="text-xs text-slate-500">{e.kind.toUpperCase()} · {fmtDateTime(e.created_at)}</div></div></li>))}</ol>}
      </Card>
    </div>
  );
}
