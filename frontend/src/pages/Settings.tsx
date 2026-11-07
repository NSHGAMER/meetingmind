import { useState } from "react";
import { api } from "../api";
import { Badge, Button, Card, CardHeader, ErrorBanner, Spinner, useLoad } from "../components/ui";

interface Info {
  user: { name: string; email: string }; hindsight: { url: string; api_key_configured: boolean; bank: string };
  llm: { provider: string; model: string; configured: boolean }; data_processing: string;
}

export default function SettingsPage() {
  const { data: i, error } = useLoad(() => api.get<Info>("/api/settings/info"));
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const test = async () => {
    setBusy(true); setStatus(null);
    try { const r = await api.get<{ url: string; bank: string }>("/api/memory/health"); setStatus({ ok: true, msg: `Connected to ${r.url} — memory bank "${r.bank}" is reachable.` }); }
    catch (e) { setStatus({ ok: false, msg: (e as Error).message }); } finally { setBusy(false); }
  };
  if (!i) return error ? <ErrorBanner error={error} /> : <Spinner />;
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-lg font-semibold text-slate-100">Settings</h1>
      <Card><CardHeader title="Account" /><div className="p-4 text-sm">{i.user.name} · {i.user.email}</div></Card>
      <Card><CardHeader title="Hindsight memory" action={<Button busy={busy} onClick={test}>Test connection</Button>} />
        <div className="space-y-1 p-4 text-sm"><div>Endpoint: <code>{i.hindsight.url}</code></div><div>Your private memory bank: <code>{i.hindsight.bank}</code></div>
          <div>API key: {i.hindsight.api_key_configured ? <Badge tone="completed">configured</Badge> : <Badge>not set (fine for a local server)</Badge>}</div>
          {status && <div className={`mt-2 rounded border px-3 py-2 ${status.ok ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200" : "border-red-500/40 bg-red-500/10 text-red-200"}`}>{status.msg}</div>}</div></Card>
      <Card><CardHeader title="AI provider & data processing" />
        <div className="space-y-2 p-4 text-sm"><div>Provider: <b>{i.llm.provider}</b> · model <code>{i.llm.model}</code> {i.llm.configured ? <Badge tone="completed">key configured</Badge> : <Badge tone="overdue">API key missing</Badge>}</div>
          <p className="text-slate-400">{i.data_processing}</p></div></Card>
    </div>
  );
}
