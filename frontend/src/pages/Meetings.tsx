import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Badge, Button, Card, Empty, ErrorBanner, Field, Modal, Spinner, fmtDateTime, useLoad } from "../components/ui";
import type { Contact, Meeting } from "../types";

export function MeetingForm({ initial, onSaved, onClose }: { initial?: Meeting; onSaved: (m: Meeting) => void; onClose: () => void }) {
  const contacts = useLoad(() => api.get<Contact[]>("/api/contacts"));
  const [f, setF] = useState({
    title: initial?.title ?? "", organization: initial?.organization ?? "", objective: initial?.objective ?? "", agenda: initial?.agenda ?? "",
    scheduled_at: (initial?.scheduled_at ?? new Date(Date.now() + 86400000).toISOString()).slice(0, 16), status: initial?.status ?? "scheduled",
  });
  const [ids, setIds] = useState<number[]>(initial?.participants.map((p) => p.id) ?? []);
  const [err, setErr] = useState<unknown>(null); const [busy, setBusy] = useState(false);

  const save = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      const body = { ...f, organization: f.organization || null, objective: f.objective || null, agenda: f.agenda || null, participant_ids: ids };
      onSaved(initial ? await api.patch<Meeting>(`/api/meetings/${initial.id}`, body) : await api.post<Meeting>("/api/meetings", body));
    } catch (x) { setErr(x); } finally { setBusy(false); }
  };

  return (
    <Modal title={initial ? "Edit meeting" : "Schedule meeting"} onClose={onClose}>
      <form onSubmit={save} className="space-y-3">
        <Field label="Title"><input required value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Date & time"><input type="datetime-local" required value={f.scheduled_at} onChange={(e) => setF({ ...f, scheduled_at: e.target.value })} /></Field>
          <Field label="Status"><select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value as Meeting["status"] })}><option value="scheduled">Scheduled</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select></Field>
        </div>
        <Field label="Organization"><input value={f.organization} onChange={(e) => setF({ ...f, organization: e.target.value })} /></Field>
        <Field label="Objective"><textarea rows={2} value={f.objective} onChange={(e) => setF({ ...f, objective: e.target.value })} /></Field>
        <Field label="Agenda"><textarea rows={3} value={f.agenda} onChange={(e) => setF({ ...f, agenda: e.target.value })} /></Field>
        <Field label="Participants">
          <div className="max-h-32 space-y-1 overflow-y-auto rounded-md border border-ink-500 p-2">
            {contacts.data?.length ? contacts.data.map((c) => (
              <label key={c.id} className="flex items-center gap-2 text-sm text-slate-200"><input type="checkbox" className="!w-auto" checked={ids.includes(c.id)}
                onChange={(e) => setIds(e.target.checked ? [...ids, c.id] : ids.filter((i) => i !== c.id))} />{c.full_name}<span className="text-xs text-slate-500">{c.organization}</span></label>
            )) : <div className="text-xs text-slate-500">Add contacts first to select participants.</div>}
          </div>
        </Field>
        <ErrorBanner error={err} />
        <div className="flex justify-end gap-2"><Button type="button" onClick={onClose}>Cancel</Button><Button variant="primary" type="submit" busy={busy}>Save</Button></div>
      </form>
    </Modal>
  );
}

export default function Meetings() {
  const { data, error, loading, reload } = useLoad(() => api.get<Meeting[]>("/api/meetings"));
  const [params, setParams] = useSearchParams();
  const [open, setOpen] = useState(false);
  useEffect(() => { if (params.get("new")) { setOpen(true); setParams({}, { replace: true }); } }, [params, setParams]);

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex items-center justify-between"><h1 className="text-lg font-semibold text-slate-100">Meetings</h1>
        <Button variant="primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Schedule meeting</Button></div>
      <ErrorBanner error={error} />
      <Card>
        {loading && !data ? <Spinner /> : !data?.length ? <Empty>No meetings yet.</Empty> : data.map((m) => (
          <Link key={m.id} to={`/meetings/${m.id}`} className="flex items-center justify-between gap-3 border-b border-ink-700 px-4 py-3 last:border-0 hover:bg-ink-700/40">
            <div className="min-w-0">
              <div className="truncate text-sm text-slate-100">{m.title} {m.is_sample && <Badge tone="sample">sample</Badge>}</div>
              <div className="text-xs text-slate-500">{fmtDateTime(m.scheduled_at)} · {m.participants.map((p) => p.full_name).join(", ") || "No participants"}</div>
            </div>
            <div className="flex shrink-0 gap-2"><Badge tone={m.status === "completed" ? "completed" : m.status === "cancelled" ? "cancelled" : "pending"}>{m.status}</Badge>
              {m.analysis_status === "confirmed" && <Badge tone="memory">in memory</Badge>}</div>
          </Link>
        ))}
      </Card>
      {open && <MeetingForm onClose={() => setOpen(false)} onSaved={() => { setOpen(false); reload(); }} />}
    </div>
  );
}
