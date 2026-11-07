import { Brain, CalendarPlus, FileText, Sparkles, UserPlus } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { Badge, Button, Card, CardHeader, Empty, ErrorBanner, Spinner, StatusBadge, fmtDate, fmtDateTime, useLoad } from "../components/ui";
import type { Commitment, Meeting } from "../types";

interface Dash {
  kpis: { total_meetings: number; upcoming_meetings: number; total_contacts: number; pending_commitments: number; completed_commitments: number };
  upcoming: Meeting[]; pending_commitments: Commitment[]; recent_meetings: Meeting[];
  recent_briefings: { id: number; meeting_id: number; mode: string; memory_count: number; created_at: string; title: string }[];
  has_sample_data: boolean;
}

export default function Dashboard() {
  const { data, error, loading, reload } = useLoad(() => api.get<Dash>("/api/dashboard"));
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);

  const demo = async (reset: boolean) => {
    setBusy(true); setErr(null);
    try { reset ? await api.del("/api/demo/reset") : await api.post("/api/demo/load"); reload(); } catch (e) { setErr(e); } finally { setBusy(false); }
  };

  if (loading && !data) return <Spinner />;
  if (!data) return <ErrorBanner error={error} />;
  const k = data.kpis;
  const next = data.upcoming[0];
  const kpis = [
    ["Total meetings", k.total_meetings], ["Upcoming", k.upcoming_meetings], ["Contacts", k.total_contacts],
    ["Pending commitments", k.pending_commitments], ["Completed commitments", k.completed_commitments],
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <ErrorBanner error={err} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {kpis.map(([l, v]) => (
          <Card key={l as string} className="p-4"><div className="text-xs text-slate-400">{l}</div><div className="mt-1 text-2xl font-semibold text-slate-100">{v}</div></Card>
        ))}
      </div>

      <Card className="p-4">
        <div className="mb-3 text-sm font-semibold text-slate-100">Quick actions</div>
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          <Button onClick={() => nav("/meetings?new=1")}><CalendarPlus className="h-4 w-4" />Schedule Meeting</Button>
          <Button onClick={() => nav("/contacts?new=1")}><UserPlus className="h-4 w-4" />Add Contact</Button>
          <Button variant="primary" disabled={!next} onClick={() => next && nav(`/meetings/${next.id}/prepare`)}><Sparkles className="h-4 w-4" />Prepare My Meeting</Button>
          <Button onClick={() => nav("/meetings")}><FileText className="h-4 w-4" />Add Meeting Notes</Button>
        </div>
      </Card>

      {k.total_meetings === 0 && (
        <Card className="flex items-center justify-between gap-4 p-4">
          <div><div className="text-sm font-medium text-slate-100">Try the 3-meeting demo</div>
            <div className="text-xs text-slate-400">Loads a sample contact (Robert, ABC Technologies) and three meetings, clearly marked as sample data. You run the analysis and confirmation yourself.</div></div>
          <Button variant="primary" busy={busy} onClick={() => demo(false)}>Load demo data</Button>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader title="Upcoming meetings" action={<Link className="text-xs text-accent-soft" to="/meetings">All meetings</Link>} />
          {data.upcoming.length === 0 ? <Empty>No upcoming meetings.</Empty> : data.upcoming.map((m) => (
            <div key={m.id} className="flex items-center justify-between gap-3 border-b border-ink-700 px-4 py-3 last:border-0">
              <Link to={`/meetings/${m.id}`} className="min-w-0">
                <div className="truncate text-sm text-slate-100">{m.title} {m.is_sample && <Badge tone="sample">sample</Badge>}</div>
                <div className="text-xs text-slate-500">{fmtDateTime(m.scheduled_at)} · {m.participants.map((p) => p.full_name).join(", ") || "No participants"}</div>
              </Link>
              <Button variant="primary" onClick={() => nav(`/meetings/${m.id}/prepare`)}><Brain className="h-4 w-4" />Prepare</Button>
            </div>
          ))}
        </Card>

        <Card>
          <CardHeader title="Pending commitments" action={<Link className="text-xs text-accent-soft" to="/commitments">Tracker</Link>} />
          {data.pending_commitments.length === 0 ? <Empty>No open commitments.</Empty> : data.pending_commitments.map((c) => (
            <div key={c.id} className="flex items-center justify-between gap-3 border-b border-ink-700 px-4 py-3 last:border-0">
              <div className="min-w-0"><div className="truncate text-sm text-slate-100">{c.owner_name}: {c.description}</div>
                <div className="text-xs text-slate-500">Due {fmtDate(c.due_date)} · from {c.meeting_title}</div></div>
              <StatusBadge status={c.status} />
            </div>
          ))}
        </Card>

        <Card>
          <CardHeader title="Recent meeting activity" />
          {data.recent_meetings.length === 0 ? <Empty>No completed meetings yet.</Empty> : data.recent_meetings.map((m) => (
            <Link key={m.id} to={`/meetings/${m.id}`} className="flex items-center justify-between border-b border-ink-700 px-4 py-3 last:border-0 hover:bg-ink-700/40">
              <div><div className="text-sm text-slate-100">{m.title}</div><div className="text-xs text-slate-500">{fmtDate(m.scheduled_at)}</div></div>
              <Badge tone={m.analysis_status === "confirmed" ? "completed" : "pending"}>{m.analysis_status === "confirmed" ? "in memory" : m.analysis_status === "pending_confirmation" ? "awaiting confirmation" : "not analysed"}</Badge>
            </Link>
          ))}
        </Card>

        <Card>
          <CardHeader title="Recent AI briefings" />
          {data.recent_briefings.length === 0 ? <Empty>No briefings generated yet.</Empty> : data.recent_briefings.map((b) => (
            <Link key={b.id} to={`/meetings/${b.meeting_id}/prepare`} className="flex items-center justify-between border-b border-ink-700 px-4 py-3 last:border-0 hover:bg-ink-700/40">
              <div><div className="text-sm text-slate-100">{b.title}</div><div className="text-xs text-slate-500">{fmtDateTime(b.created_at)}</div></div>
              {b.mode === "memory" ? <Badge tone="memory"><Brain className="h-3 w-3" />{b.memory_count} facts recalled</Badge> : <Badge>generic</Badge>}
            </Link>
          ))}
        </Card>
      </div>
      {data.has_sample_data && <div className="text-right"><Button variant="danger" busy={busy} onClick={() => demo(true)}>Remove sample data</Button></div>}
    </div>
  );
}
