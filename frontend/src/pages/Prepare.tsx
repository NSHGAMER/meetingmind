import { Brain, DatabaseZap, Lightbulb, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { Badge, Button, Card, CardHeader, Empty, ErrorBanner, Spinner, StatusBadge, fmtDate, fmtDateTime, useLoad } from "../components/ui";
import type { Briefing, Cited, Meeting } from "../types";

function Sources({ sources, refs }: { sources: string[]; refs: Briefing["references"] }) {
  if (!sources?.length) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-middle">
      {sources.map((s) => {
        const r = refs[s]; if (!r) return null;
        const label = r.source_meeting ? `${fmtDate(r.source_meeting.date)} · ${r.source_meeting.title}` : "Hindsight memory";
        return <span key={s} title={r.text} className="rounded border border-indigo-500/30 bg-indigo-500/10 px-1.5 py-0.5 text-[10px] text-indigo-300">{s} · {label}</span>;
      })}
    </span>
  );
}

function Section({ letter, title, children, ai }: { letter: string; title: string; children: React.ReactNode; ai?: boolean }) {
  return (
    <Card>
      <CardHeader title={`${letter}. ${title}`} action={ai ? <Badge tone="sample"><Lightbulb className="h-3 w-3" />AI recommendation</Badge> : <Badge tone="memory"><DatabaseZap className="h-3 w-3" />Retrieved fact</Badge>} />
      <div className="space-y-2 p-4 text-sm">{children}</div>
    </Card>
  );
}

const Items = ({ items, refs, none }: { items: Cited[]; refs: Briefing["references"]; none: string }) =>
  items.length ? <ul className="list-disc space-y-1.5 pl-5">{items.map((i, k) => <li key={k}>{i.text}<Sources sources={i.sources} refs={refs} />{i.reason && <div className="text-xs text-slate-500">{i.reason}</div>}</li>)}</ul> : <div className="text-slate-500">{none}</div>;

function BriefingView({ b }: { b: Briefing }) {
  const d = b.draft, o = b.overview;
  return (
    <div className="space-y-4">
      {b.memory_used ? (
        <div className="flex items-center gap-3 rounded-lg border border-indigo-500/40 bg-indigo-500/10 px-4 py-3">
          <DatabaseZap className="h-5 w-5 text-indigo-300" />
          <div className="text-sm"><b className="text-indigo-200">Retrieved from Hindsight:</b> {b.memories_retrieved} historical facts and {b.pending_commitments.length} open commitment(s) from {o.previous_meetings.length} previous meeting(s) were used for this briefing.</div>
        </div>
      ) : (
        <div className="flex items-center gap-3 rounded-lg border border-slate-500/40 bg-slate-500/10 px-4 py-3 text-sm text-slate-300">
          <Brain className="h-5 w-5 text-slate-400" /><div><b>Generic briefing — no memory used.</b> {b.notes.join(" ")}</div>
        </div>
      )}
      {b.memory_used && b.notes.length > 0 && <div className="text-xs text-amber-300">{b.notes.join(" ")}</div>}

      <Section letter="A" title="Meeting overview">
        <div><b>{o.title}</b></div>
        <div className="text-slate-400">Participants: {o.participants.map((p) => `${p.name}${p.job_title ? ` (${p.job_title}${p.organization ? `, ${p.organization}` : ""})` : ""}`).join("; ") || "—"}</div>
        {o.objective && <div className="text-slate-400">Objective: {o.objective}</div>}
        <div className="text-slate-400">Previous interactions: {o.previous_meetings.length ? o.previous_meetings.map((m) => `${m.title} (${fmtDate(m.date)})`).join(" → ") : "None on record"}</div>
        {d.previous_interactions_summary && b.memory_used && <div className="text-slate-300">{d.previous_interactions_summary}</div>}
      </Section>

      {b.memory_used && <>
        <Section letter="B" title="Historical context">
          <div className="text-xs font-semibold uppercase text-slate-400">Discussed & decided</div><Items items={d.historical_context} refs={b.references} none="Nothing recorded." />
          <div className="pt-2 text-xs font-semibold uppercase text-slate-400">Previous concerns</div><Items items={d.previous_concerns} refs={b.references} none="No concerns on record." />
        </Section>
        <Section letter="C" title="Pending commitments">
          {b.pending_commitments.length === 0 ? <div className="text-slate-500">No open commitments.</div> : b.pending_commitments.map((c) => (
            <div key={c.id} className="flex items-start justify-between gap-3 rounded border border-ink-600 bg-ink-700/40 px-3 py-2">
              <div><div><b>{c.owner_name}</b> — {c.description}</div><div className="text-xs text-slate-500">Due {fmtDate(c.due_date)} · promised in {c.source_meeting?.title} ({fmtDate(c.source_meeting?.date)}) · from commitment tracker</div></div>
              <StatusBadge status={c.status} />
            </div>))}
        </Section>
        <Section letter="D" title="Important things to remember"><Items items={d.things_to_remember} refs={b.references} none="Nothing additional on record." /></Section>
      </>}

      <Section letter={b.memory_used ? "E" : "B"} title="Suggested talking points" ai><Items items={d.talking_points} refs={b.references} none="No suggestions." /></Section>
      <Section letter={b.memory_used ? "F" : "C"} title="Recommended meeting strategy" ai>
        {d.strategy.length ? <ul className="list-disc space-y-1.5 pl-5">{d.strategy.map((s, i) => <li key={i}>{s}</li>)}</ul> : <div className="text-slate-500">No recommendations.</div>}
      </Section>
      {b.processing_notice && <div className="text-xs text-slate-500">{b.processing_notice}</div>}
    </div>
  );
}

export default function Prepare() {
  const { id } = useParams();
  const { data: m, error } = useLoad(() => api.get<Meeting>(`/api/meetings/${id}`), [id]);
  const [res, setRes] = useState<{ memory?: Briefing; generic?: Briefing }>({});
  const [tab, setTab] = useState<"memory" | "generic">("memory");
  const [busy, setBusy] = useState(""); const [err, setErr] = useState<unknown>(null);

  const gen = async (mode: "memory" | "generic") => {
    setBusy(mode); setErr(null);
    try {
      const b = await api.post<Briefing>(`/api/meetings/${id}/prepare?mode=${mode}`);
      setRes((r) => ({ ...r, [mode]: b })); setTab(mode);
    } catch (e) { setErr(e); } finally { setBusy(""); }
  };
  const compare = async () => { await gen("generic"); await gen("memory"); };

  if (!m) return error ? <ErrorBanner error={error} /> : <Spinner />;
  const cur = res[tab];

  return (
    <div className="mx-auto grid max-w-6xl gap-5 lg:grid-cols-[280px_1fr]">
      <aside className="space-y-4">
        <Card>
          <CardHeader title="Meeting" />
          <div className="space-y-3 p-4 text-sm">
            <Link to={`/meetings/${m.id}`} className="font-medium text-slate-100 hover:text-accent-soft">{m.title}</Link>
            <div className="text-slate-400">{fmtDateTime(m.scheduled_at)}</div>
            <div><div className="text-xs text-slate-500">Participants</div>{m.participants.map((p) => <div key={p.id}><Link to={`/contacts/${p.id}`} className="text-accent-soft">{p.full_name}</Link><div className="text-xs text-slate-500">{[p.job_title, p.organization].filter(Boolean).join(", ")}</div></div>)}{!m.participants.length && <span className="text-slate-500">None — add participants for memory recall</span>}</div>
            {m.objective && <div><div className="text-xs text-slate-500">Objective</div>{m.objective}</div>}
            {m.agenda && <div><div className="text-xs text-slate-500">Agenda</div><div className="whitespace-pre-line">{m.agenda}</div></div>}
          </div>
        </Card>
        <Card className="space-y-2 p-4">
          <Button variant="primary" className="w-full" busy={busy === "memory"} onClick={() => gen("memory")}><Sparkles className="h-4 w-4" />PREPARE MY MEETING</Button>
          <Button className="w-full" busy={busy === "generic"} onClick={() => gen("generic")}>Generic AI (no memory)</Button>
          <Button className="w-full" disabled={!!busy} onClick={compare}>Compare: generic vs memory</Button>
        </Card>
      </aside>

      <section className="space-y-4">
        <ErrorBanner error={err} />
        {(res.memory || res.generic) && (
          <div className="flex gap-1 rounded-md border border-ink-600 bg-ink-800 p-1 text-sm">
            {(["memory", "generic"] as const).map((t) => (
              <button key={t} disabled={!res[t]} onClick={() => setTab(t)} className={`flex-1 rounded px-3 py-1.5 ${tab === t ? "bg-ink-500 text-white" : "text-slate-400 disabled:opacity-40"}`}>
                {t === "memory" ? "Memory-powered (Hindsight)" : "Generic AI"}</button>))}
          </div>)}
        {busy && <Spinner label={busy === "memory" ? "Recalling from Hindsight and generating briefing…" : "Generating generic briefing…"} />}
        {!busy && cur && <BriefingView b={cur} />}
        {!busy && !cur && <Card><Empty>Click <b>Prepare my meeting</b> to recall history from Hindsight and generate a briefing. Use “Compare” to see a generic response next to the memory-powered one.</Empty></Card>}
      </section>
    </div>
  );
}
