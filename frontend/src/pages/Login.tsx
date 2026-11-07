import { Brain } from "lucide-react";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { Button, ErrorBanner, Field } from "../components/ui";

export default function Login() {
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState(""); const [email, setEmail] = useState(""); const [pw, setPw] = useState("");
  const [err, setErr] = useState<unknown>(null); const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { mode === "login" ? await login(email, pw) : await register(name, email, pw); } catch (x) { setErr(x); } finally { setBusy(false); }
  };

  return (
    <div className="grid min-h-full place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-lg border border-ink-600 bg-ink-800 p-6">
        <div className="flex items-center gap-2"><div className="grid h-8 w-8 place-items-center rounded-md bg-accent"><Brain className="h-4 w-4 text-white" /></div>
          <div><div className="font-semibold text-slate-100">MeetingMind</div><div className="text-xs text-slate-500">Never walk into a meeting without remembering what happened before.</div></div></div>
        {mode === "register" && <Field label="Full name"><input value={name} onChange={(e) => setName(e.target.value)} required /></Field>}
        <Field label="Email"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></Field>
        <Field label="Password (min 8 characters)"><input type="password" value={pw} onChange={(e) => setPw(e.target.value)} required minLength={8} maxLength={72} /></Field>
        <ErrorBanner error={err} />
        <Button variant="primary" type="submit" busy={busy} className="w-full">{mode === "login" ? "Log in" : "Create account"}</Button>
        <button type="button" className="w-full text-center text-xs text-slate-400 hover:text-slate-200" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "No account? Register" : "Have an account? Log in"}
        </button>
      </form>
    </div>
  );
}
