import { Brain, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Badge, Button, Card, CardHeader, Empty, ErrorBanner, Spinner, StatusBadge, fmtDate, useLoad } from "../components/ui";
import type { Contact } from "../types";
import { ContactForm } from "./Contacts";

interface Item { text: string; topic?: string; meeting_id: number; meeting_title: string; date: string }
interface Profile {
  contact: Contact; relationship_summary: string;
  meetings: { id: number; title: string; date: string; status: string; analysis_status: string }[];
  discussions: Item[]; decisions: Item[]; concerns: Item[]; preferences: Item[];
  commitments: { id: number; description: string; owner_name: string; due_date: string | null; status: string; meeting_id: number }[];
  topics: { topic: string; count: number }[];
  timeline: { type: string; date: string; title: string; meeting_id: number; status: string }[];
  hindsight_memories: { text: string; meeting_id: number | null; type: string | null }[]; hindsight_error: string | null;
}

const List = ({ title, items }: { title: string; items: Item[] }) => (
  <Card><CardHeader title={title} />
    {items.length === 0 ? <Empty>Nothing recorded.</Empty> : <ul className="divide-y divide-ink-700">{items.map((i, k) => (
      <li key={k} className="px-4 py-2.5 text-sm"><div>{i.text} {i.topic && <Badge>{i.topic}</Badge>}</div><div className="text-xs text-slate-500">{fmtDate(i.date)} · {i.meeting_title}</div></li>))}</ul>}
  </Card>
);

export default function ContactProfile() {
  const { id } = useParams(); const nav = useNavigate();
  const { data: p, error, loading, reload } = useLoad(() => api.get<Profile>(`/api/contacts/${id}/profile`), [id]);
  const [edit, setEdit] = useState(false);
  if (loading && !p) return <Spinner label="Loading profile and recalling from Hindsight…" />;
  if (!p) return <ErrorBanner error={error} />;
  const c = p.contact;

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <Card className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold text-slate-100">{c.full_name} {c.is_sample && <Badge tone="sample">sample</Badge>}</h1>
            <div className="text-sm text-slate-400">{[c.job_title, c.organization].filter(Boolean).join(" · ")}</div>
            <div className="text-xs text-slate-500">{c.email}</div>
            {c.description && <p className="mt-2 text-sm text-slate-300">{c.description}</p>}
            {c.relationship_notes && <p className="text-sm text-slate-400">Notes: {c.relationship_notes}</p>}
          </div>
          <div className="flex gap-1"><Button onClick={() => setEdit(true)}><Pencil className="h-4 w-4" /></Button>
            <Button variant="danger" onClick={async () => { if (window.confirm("Delete this contact?")) { await api.del(`/api/contacts/${c.id}`); nav("/contacts"); } }}><Trash2 className="h-4 w-4" /></Button></div>
        </div>
      </Card>

      <Card className="border-indigo-500/30 p-4">
        <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-indigo-200"><Brain className="h-4 w-4" />Relationship intelligence <span className="text-xs font-normal text-slate-500">built from confirmed meeting records</span></div>
        <p className="text-sm text-slate-200">{p.relationship_summary}</p>
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card><CardHeader title="Previous meetings" />
          {p.meetings.length === 0 ? <Empty>No meetings with this contact.</Empty> : p.meetings.map((m) => (
            <Link key={m.id} to={`/meetings/${m.id}`} className="flex items-center justify-between border-b border-ink-700 px-4 py-2.5 text-sm last:border-0 hover:bg-ink-700/40">
              <span>{m.title}<div className="text-xs text-slate-500">{fmtDate(m.date)}</div></span>
              <Badge tone={m.analysis_status === "confirmed" ? "memory" : "neutral"}>{m.analysis_status === "confirmed" ? "in memory" : m.status}</Badge></Link>))}
        </Card>
        <Card><CardHeader title="Commitments" />
          {p.commitments.length === 0 ? <Empty>None.</Empty> : p.commitments.map((x) => (
            <div key={x.id} className="flex items-center justify-between border-b border-ink-700 px-4 py-2.5 text-sm last:border-0"><span>{x.description}<div className="text-xs text-slate-500">Due {fmtDate(x.due_date)}</div></span><StatusBadge status={x.status} /></div>))}
        </Card>
        <List title="Important discussions" items={p.discussions} />
        <List title="Decisions" items={p.decisions} />
        <List title="Concerns" items={p.concerns} />
        <List title="Preferences" items={p.preferences} />
      </div>

      <Card><CardHeader title="Interaction timeline" />
        {p.timeline.length === 0 ? <Empty>No interactions yet.</Empty> : <ol className="space-y-3 p-4">{p.timeline.map((t, i) => (
          <li key={i} className="flex gap-3 text-sm"><span className="w-24 shrink-0 text-xs text-slate-500">{fmtDate(t.date)}</span><span className={t.type === "meeting" ? "text-slate-100" : "text-slate-300"}>{t.type === "meeting" ? "Meeting: " : "Commitment: "}{t.title} <StatusBadge status={t.status} /></span></li>))}</ol>}
      </Card>

      <Card><CardHeader title="Raw memories recalled from Hindsight" sub="Live recall for this contact" />
        {p.hindsight_error ? <div className="p-4"><ErrorBanner error={{ code: "hindsight_unavailable", message: p.hindsight_error }} /></div>
          : p.hindsight_memories.length === 0 ? <Empty>No memories stored for this contact yet. Confirm a meeting’s notes to create some.</Empty>
            : <ul className="divide-y divide-ink-700">{p.hindsight_memories.map((m, i) => <li key={i} className="px-4 py-2.5 text-sm text-slate-300">{m.text}</li>)}</ul>}
      </Card>
      {edit && <ContactForm initial={c} onClose={() => setEdit(false)} onSaved={() => { setEdit(false); reload(); }} />}
    </div>
  );
}
