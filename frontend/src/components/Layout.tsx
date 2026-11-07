import { Brain, CalendarDays, CheckSquare, LayoutDashboard, LogOut, Search, Settings, Users } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/meetings", label: "Meetings", icon: CalendarDays },
  { to: "/contacts", label: "Contacts", icon: Users },
  { to: "/commitments", label: "Commitments", icon: CheckSquare },
  { to: "/memory", label: "Memory Intelligence", icon: Brain },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const nav2 = useNavigate();
  const [q, setQ] = useState("");
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div className="flex h-full">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-ink-600 bg-ink-950/60 p-3 md:flex">
        <div className="mb-6 flex items-center gap-2 px-2 pt-1">
          <div className="grid h-7 w-7 place-items-center rounded-md bg-accent"><Brain className="h-4 w-4 text-white" /></div>
          <span className="font-semibold text-slate-100">MeetingMind</span>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5">
          {nav.map(({ to, label, icon: I, end }) => (
            <NavLink key={to} to={to} end={end}
              className={({ isActive }) => `flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm ${isActive ? "bg-ink-600 text-white" : "text-slate-400 hover:bg-ink-700 hover:text-slate-200"}`}>
              <I className="h-4 w-4" />{label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-ink-600 pt-3">
          <div className="px-2 text-xs text-slate-400">{user?.name}</div>
          <div className="truncate px-2 pb-2 text-[11px] text-slate-500">{user?.email}</div>
          <button onClick={logout} className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-sm text-slate-400 hover:bg-ink-700"><LogOut className="h-4 w-4" />Log out</button>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-ink-600 px-6 py-3">
          <div>
            <div className="text-sm font-medium text-slate-100">{greet}, {user?.name?.split(" ")[0]}</div>
            <div className="text-xs text-slate-500">{new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</div>
          </div>
          <form className="relative w-64 max-w-[45%]" onSubmit={(e) => { e.preventDefault(); nav2(`/contacts?q=${encodeURIComponent(q)}`); }}>
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
            <input className="pl-8" placeholder="Search contacts…" value={q} onChange={(e) => setQ(e.target.value)} />
          </form>
        </header>
        <div className="flex gap-1 overflow-x-auto border-b border-ink-600 px-3 py-2 md:hidden">
          {nav.map(({ to, label, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `whitespace-nowrap rounded px-2 py-1 text-xs ${isActive ? "bg-ink-600 text-white" : "text-slate-400"}`}>{label}</NavLink>
          ))}
        </div>
        <main className="flex-1 overflow-y-auto p-6"><Outlet /></main>
      </div>
    </div>
  );
}
