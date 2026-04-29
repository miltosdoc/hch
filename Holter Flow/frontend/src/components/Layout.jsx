import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, CalendarDays, Server, BookOpen, Package, LogOut, Activity } from 'lucide-react';
import newLogo from '../assets/new_logo.png';

const NAV = [
  { to: '/',         label: 'Dashboard',       icon: LayoutDashboard },
  { to: '/schedule', label: 'Veckoschema',     icon: CalendarDays },
  { to: '/devices',  label: 'Enhetsregister',  icon: Server },
  { to: '/postal',   label: 'Posthantering',   icon: Package },
  { to: '/active',   label: 'Utcheckade',      icon: Activity },
  { to: '/guide',    label: 'Guide',           icon: BookOpen },
];

export default function Layout({ children, onLogout }) {
  const { pathname } = useLocation();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Sidebar ───────────────────────────────── */}
      <aside className="w-60 bg-navy-900 flex flex-col flex-shrink-0 border-r border-white/[0.07]">

        {/* Brand bar — Prominent Pulsus title with new logo */}
        <div className="px-6 py-8 flex flex-col items-center justify-center gap-3 border-b border-white/[0.07]">
          <img src={newLogo} alt="Pulsus Logo" className="w-28 opacity-85" />
          <span className="text-3xl font-black text-white tracking-widest uppercase" style={{ fontFamily: "'Montserrat', sans-serif" }}>
            Pulsus
          </span>
          <span className="text-[10px] text-slate-500 tracking-widest uppercase font-medium -mt-1">
            Holter Tracker
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-1">
          {NAV.map(({ to, label, icon: Icon }) => {
            const active = pathname === to;
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150
                  ${active
                    ? 'bg-pulse-500/20 text-pulse-300 border border-pulse-400/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                  }`}
              >
                <Icon size={17} className={active ? 'text-pulse-400' : 'text-slate-500'} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Logout */}
        {onLogout && (
          <div className="px-3 pb-4 border-t border-white/[0.06] pt-3">
            <button
              onClick={onLogout}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:text-red-400 hover:bg-red-500/5 transition-all w-full"
            >
              <LogOut size={17} />
              Logga ut
            </button>
          </div>
        )}
      </aside>

      {/* ── Main area ─────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-50">

        {/* Top bar */}
        <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
          <h1 className="text-sm font-semibold text-slate-700">
            {NAV.find(n => n.to === pathname)?.label ?? 'Pulsus'}
          </h1>
          <div className="flex items-center gap-3">
            <span className="badge bg-pulse-500/10 text-pulse-600 border border-pulse-400/20">
              <span className="dot bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
              Pulsus Holter
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto px-6 pt-6 bg-slate-50">
          {children}
        </main>
      </div>
    </div>
  );
}
