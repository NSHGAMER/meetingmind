import { Brain, Check, Pencil, Sparkles, Trash2, Upload, X } from "lucide-react";
import { useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Badge, Button, Card, CardHeader, ErrorBanner, Spinner, fmtDateTime, useLoad } from "../components/ui";
import type { Extraction, Meeting } from "../types";
import { MeetingForm } from "./Meetings";

type Analysis = { extraction: Extraction; processing_notice: string };

function RemovableList<T>({ title, items, render, onRemove }: { title: string; items: T[]; render: (i: T) => React.ReactNode; onRemove: (idx: number) => void }) {
  if (!items.length) return null;
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</div>
      <ul className="space-y-1">{items.map((it, i) => (
        <li key={i} className="flex items-start justify-between gap-2 rounded border border-ink-600 bg-ink-700/50 px-2.5 py-1.5 text-sm">
          <div>{render(it)}</div>
          <button title="Remove from memory" onClick={() => onRemove(i)} className="text-slate-500 hover:text-red-300"><X className="h-4 w-4" /></button>
        </li>))}
      </ul>
    </div>
  );
}

export default function MeetingDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { data: m, error, loading, reload } = useLoad(() => api.get<Meeting>(`/api/meetings/${id}`), [id]);
  const [notes, setNotes] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [accepted, setAccepted] = useState<number[]>([]);
  const [busy, setBusy] = useState<string>("");
  const [err, setErr] = useState<unknown>(null);
  const [edit, setEdit] = useState(false);
  const [done, setDone] = useState<string[] | null>(null);
  const [ack, setAck] = useState(localStorage.getItem("mm_ack") === "1");
  const fileRef = useRef<HTMLInputElement>(null);

  if (loading && !m) return <Spinner />;
  if (!m) return <ErrorBanner error={error} />;
  const text = notes ?? m.notes ?? "";

  const run = async (label: string, fn: () => Promise<void>) => { setBusy(label); setErr(null); try { await fn(); } catch (e) { setErr(e); } finally { setBusy(""); } };
  const analyze = () => run("analyze", async () => {
    setDone(null);
    setAnalysis(await api.post<Analysis>(`/api/meetings/${m.id}/analyze`, { notes: text }));
    setAccepted([]); reload();
  });
  const loadPending = () => run("load", async () => setAnalysis(await api.get<Analysis>(`/api/meetings/${m.id}/analysis`)));
  const upload = (f: File) => run("upload", async () => { const r = await api.upload<Meeting>(`/api/meetings/${m.id}/notes/upload`, f); setNotes(r.notes ?? ""); });
  const confirm = () => run("confirm", async () => {
    const r = await api.post<{ warnings: string[] }>(`/api/meetings/${m.id}/confirm`, { extraction: analysis!.extraction, accepted_status_update_ids: accepted });
    setDone(r.warnings); setAnalysis(null); reload();
  });
  const ex = analysis?.extraction;
  const patch = (k: keyof Extraction, idx: number) => setAnalysis({ ...analysis!, extraction: { ...ex!, [k]: (ex![k] as unknown[]).filter((_, i) => i !== idx) } as Extraction });

  return (
    <div className="mx-auto grid max-w-6xl gap-5 lg:grid-cols-3">
      <div className="space-y-4">
        <Card>
          <CardHeader title={m.title} action={<div className="flex gap-1"><button className="p-1 text-slate-400 hover:text-slate-100" onClick={() => setEdit(true)}><Pencil className="h-4 w-4" /></button>
            <button className="p-1 text-slate-400 hover:text-red-300" onClick={async () => { if (confirmDel()) { await api.del(`/api/meetings/${m.id}`); nav("/meetings"); } }}><Trash2 className="h-4 w-4" /></button></div>} />
          <div className="space-y-3 p-4 text-sm">
            <div className="flex flex-wrap gap-2">{m.is_sample && <Badge tone="sample">sample</Badge>}<Badge>{m.status}</Badge><Badge tone={m.analysis_status === "confirmed" ? "memory" : "neutral"}>{m.analysis_status.replace("_", " ")}</Badge></div>
            <div className="text-slate-300">{fmtDateTime(m.scheduled_at)}</div>
            {m.organization && <div className="text-slate-400">{m.organization}</div>}
            <div><div className="text-xs text-slate-500">Participants</div>{m.participants.length ? m.participants.map((p) => <Link key={p.id} to={`/contacts/${p.id}`} className="block text-accent-soft">{p.full_name}</Link>) : <span className="text-slate-500">None</span>}</div>
            {m.objective && <div><div className="text-xs text-slate-500">Objective</div>{m.objective}</div>}
            {m.agenda && <div><div className="text-xs text-slate-500">Agenda</div><div className="whitespace-pre-line">{m.agenda}</div></div>}
            <Button variant="primary" className="w-full" onClick={() => nav(`/meetings/${m.id}/prepare`)}><Sparkles className="h-4 w-4" />Prepare my meeting</Button>
          </div>
        </Card>
      </div>

      <div className="space-y-4 lg:col-span-2">
        <ErrorBanner error={err} />
        {done && <div className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200"><Check className="mr-1 inline h-4 w-4" />Confirmed and stored in Hindsight memory.{done.map((w) => <div key={w} className="text-amber-300">{w}</div>)}</div>}
        <Card>
          <CardHeader title="Meeting notes" sub="Type notes or upload .txt, .md, .docx or .pdf (max 2 MB)"
            action={<><input ref={fileRef} type="file" hidden accept=".txt,.md,.docx,.pdf" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
              <Button busy={busy === "upload"} onClick={() => fileRef.current?.click()}><Upload className="h-4 w-4" />Upload</Button></>} />
          <div className="space-y-3 p-4">
            <textarea rows={9} value={text} onChange={(e) => setNotes(e.target.value)} placeholder="Paste or type what happened in the meeting…" />
            <label className="flex items-start gap-2 text-xs text-slate-400"><input type="checkbox" className="!mt-0.5 !w-auto" checked={ack} onChange={(e) => { setAck(e.target.checked); localStorage.setItem("mm_ack", e.target.checked ? "1" : "0"); }} />
              I understand these notes are sent to the configured LLM provider for analysis, and only facts I confirm are stored in my private Hindsight memory (see Settings).</label>
            <div className="flex gap-2">
              <Button variant="primary" disabled={!ack || !text.trim()} busy={busy === "analyze"} onClick={analyze}><Brain className="h-4 w-4" />Analyse notes</Button>
              {m.analysis_status === "pending_confirmation" && !analysis && <Button busy={busy === "load"} onClick={loadPending}>Review pending extraction</Button>}
            </div>
          </div>
        </Card>

        {ex && (
          <Card>
            <CardHeader title="Review extracted information" sub="Nothing is saved until you confirm. Remove anything that is wrong." />
            <div className="space-y-4 p-4 text-sm">
              <div className="rounded border border-ink-600 bg-ink-700/50 p-3"><div className="mb-1 text-xs font-semibold uppercase text-slate-400">Summary</div>{ex.summary}</div>
              <RemovableList title="Discussions" items={ex.discussions} onRemove={(i) => patch("discussions", i)} render={(d) => <>{d.text} {d.topic && <Badge>{d.topic}</Badge>}</>} />
              <RemovableList title="Decisions" items={ex.decisions} onRemove={(i) => patch("decisions", i)} render={(d) => <>{d.text} <Badge>{d.status}</Badge></>} />
              <RemovableList title="Commitments & suggestions" items={ex.commitments} onRemove={(i) => patch("commitments", i)}
                render={(c) => <><b>{c.owner_name}</b> — {c.description} <span className="text-slate-500">(due {c.due_date ?? "no date"})</span> {c.kind === "commitment" ? <Badge tone="pending">confirmed commitment</Badge> : <Badge>suggestion only</Badge>}</>} />
              <RemovableList title="Concerns" items={ex.concerns} onRemove={(i) => patch("concerns", i)} render={(c) => <>{c.text} {c.raised_by && <span className="text-slate-500">— {c.raised_by}</span>}</>} />
              <RemovableList title="Preferences" items={ex.preferences} onRemove={(i) => patch("preferences", i)} render={(c) => <>{c.text} {c.person && <span className="text-slate-500">— {c.person}</span>}</>} />
              <RemovableList title="Unresolved issues" items={ex.unresolved} onRemove={(i) => patch("unresolved", i)} render={(c) => <>{c}</>} />
              <RemovableList title="Follow-up actions" items={ex.follow_ups} onRemove={(i) => patch("follow_ups", i)} render={(c) => <>{c}</>} />
              {ex.suggested_status_updates.length > 0 && (
                <div><div className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-300">Suggested changes to existing commitments (applied only if you tick them)</div>
                  {ex.suggested_status_updates.map((u) => (
                    <label key={u.commitment_id} className="flex items-start gap-2 rounded border border-amber-500/30 bg-amber-500/5 px-2.5 py-1.5">
                      <input type="checkbox" className="!mt-1 !w-auto" checked={accepted.includes(u.commitment_id)} onChange={(e) => setAccepted(e.target.checked ? [...accepted, u.commitment_id] : accepted.filter((i) => i !== u.commitment_id))} />
                      <span>Commitment #{u.commitment_id} → <b>{u.suggested_status.replace("_", " ")}</b> <span className="text-slate-500">{u.evidence}</span></span></label>))}
                </div>)}
              <div className="flex items-center justify-between gap-3 border-t border-ink-600 pt-3">
                <span className="text-xs text-slate-400">{analysis!.processing_notice}</span>
                <Button variant="primary" busy={busy === "confirm"} onClick={confirm}><Check className="h-4 w-4" />Confirm & save to memory</Button>
              </div>
            </div>
          </Card>
        )}
      </div>
      {edit && <MeetingForm initial={m} onClose={() => setEdit(false)} onSaved={() => { setEdit(false); reload(); }} />}
    </div>
  );
}
const confirmDel = () => window.confirm("Delete this meeting and its extracted records? Memories already stored in Hindsight are not removed.");
