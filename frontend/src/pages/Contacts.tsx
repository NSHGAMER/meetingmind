import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Badge, Button, Card, Empty, ErrorBanner, Field, Modal, Spinner, useLoad } from "../components/ui";
import type { Contact } from "../types";

export function ContactForm({ initial, onSaved, onClose }: { initial?: Contact; onSaved: () => void; onClose: () => void }) {
  const [f, setF] = useState({ full_name: initial?.full_name ?? "", email: initial?.email ?? "", organization: initial?.organization ?? "", job_title: initial?.job_title ?? "", description: initial?.description ?? "", relationship_notes: initial?.relationship_notes ?? "" });
  const [err, setErr] = useState<unknown>(null); const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });
  const save = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    const body = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === "" ? null : v]));
    try { initial ? await api.put(`/api/contacts/${initial.id}`, body) : await api.post("/api/contacts", body); onSaved(); } catch (x) { setErr(x); } finally { setBusy(false); }
  };
  return (
    <Modal title={initial ? "Edit contact" : "Add contact"} onClose={onClose}>
      <form onSubmit={save} className="space-y-3">
        <Field label="Full name"><input required value={f.full_name} onChange={set("full_name")} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Email"><input type="email" value={f.email} onChange={set("email")} /></Field>
          <Field label="Job title"><input value={f.job_title} onChange={set("job_title")} /></Field>
        </div>
        <Field label="Organization"><input value={f.organization} onChange={set("organization")} /></Field>
        <Field label="Description"><textarea rows={2} value={f.description} onChange={set("description")} /></Field>
        <Field label="Relationship notes"><textarea rows={2} value={f.relationship_notes} onChange={set("relationship_notes")} /></Field>
        <ErrorBanner error={err} />
        <div className="flex justify-end gap-2"><Button type="button" onClick={onClose}>Cancel</Button><Button variant="primary" type="submit" busy={busy}>Save</Button></div>
      </form>
    </Modal>
  );
}

export default function Contacts() {
  const { data, error, loading, reload } = useLoad(() => api.get<Contact[]>("/api/contacts"));
  const [params, setParams] = useSearchParams();
  const [open, setOpen] = useState(false);
  const q = (params.get("q") ?? "").toLowerCase();
  useEffect(() => { if (params.get("new")) { setOpen(true); const p = new URLSearchParams(params); p.delete("new"); setParams(p, { replace: true }); } }, [params, setParams]);
  const rows = (data ?? []).filter((c) => !q || `${c.full_name} ${c.organization ?? ""} ${c.email ?? ""}`.toLowerCase().includes(q));

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex items-center justify-between"><h1 className="text-lg font-semibold text-slate-100">Contacts {q && <span className="text-sm font-normal text-slate-500">matching “{q}”</span>}</h1>
        <Button variant="primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Add contact</Button></div>
      <ErrorBanner error={error} />
      <Card>
        {loading && !data ? <Spinner /> : !rows.length ? <Empty>No contacts found.</Empty> : rows.map((c) => (
          <Link key={c.id} to={`/contacts/${c.id}`} className="flex items-center justify-between border-b border-ink-700 px-4 py-3 last:border-0 hover:bg-ink-700/40">
            <div><div className="text-sm text-slate-100">{c.full_name} {c.is_sample && <Badge tone="sample">sample</Badge>}</div>
              <div className="text-xs text-slate-500">{[c.job_title, c.organization].filter(Boolean).join(" · ") || "—"}</div></div>
            <div className="text-xs text-slate-500">{c.email}</div>
          </Link>))}
      </Card>
      {open && <ContactForm onClose={() => setOpen(false)} onSaved={() => { setOpen(false); reload(); }} />}
    </div>
  );
}
