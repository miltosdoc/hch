import { useState, useEffect, useCallback } from 'react';
import { getFleetStatus, getCapacity, fetchExams, syncWebdocExams } from '../services/api';
import { Activity, Cpu, Package, BarChart3, RefreshCw, AlertTriangle, CalendarCheck, Zap } from 'lucide-react';

const STATUS_META = {
  available:   { label: 'Tillgänglig',   dot: 'bg-emerald-500 shadow-[0_0_8px_rgba(52,211,153,0.4)]', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  on_patient:  { label: 'På Patient',    dot: 'bg-pulse-500  shadow-[0_0_8px_rgba(129,140,248,0.4)]', badge: 'bg-indigo-50  text-indigo-700  border-indigo-200' },
  in_transit:  { label: 'Under Post',    dot: 'bg-amber-500  shadow-[0_0_8px_rgba(251,191,36,0.4)]',  badge: 'bg-amber-50  text-amber-700  border-amber-200' },
  returned:    { label: 'Returnerad',    dot: 'bg-teal-500',  badge: 'bg-teal-50   text-teal-700   border-teal-200' },
  maintenance: { label: 'Underhåll',     dot: 'bg-rose-500',  badge: 'bg-rose-50   text-rose-700   border-rose-200' },
  lost:        { label: 'Borttappad',    dot: 'bg-red-600',   badge: 'bg-red-50    text-red-700    border-red-200' },
  assigned:    { label: 'Tilldelad',     dot: 'bg-blue-500',  badge: 'bg-blue-50   text-blue-700   border-blue-200' },
  processing:  { label: 'Bearbetning',   dot: 'bg-orange-500',badge: 'bg-orange-50 text-orange-700 border-orange-200' },
};

export default function Dashboard() {
  const [fleet, setFleet]     = useState(null);
  const [capacity, setCapacity] = useState(null);
  const [exams, setExams]     = useState([]);
  const [error, setError]     = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastSync, setLastSync] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);

  const load = useCallback(async () => {
    setRefreshing(true); setError(null);
    try {
      const [fr, cr, er] = await Promise.all([getFleetStatus(), getCapacity(), fetchExams()]);
      setFleet(fr.data);
      setCapacity(cr.data);
      setExams(er.data ?? []);
      setLastSync(new Date().toLocaleTimeString('sv-SE'));
    } catch {
      setError('Backenden är offline — starta Docker och försök igen.');
    } finally { setRefreshing(false); }
  }, []);

  // Auto-sync from Webdoc on first load
  useEffect(() => {
    const doInitialSync = async () => {
      try {
        const res = await syncWebdocExams();
        const data = res.data;
        if (data.new > 0 || data.cancelled > 0) {
          setSyncStatus(`Synkade ${data.new} nya, ${data.cancelled} avbokade`);
        }
      } catch { /* silent */ }
      load();
    };
    doInitialSync();
  }, [load]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, [load]);

  const counts  = fleet?.counts  ?? {};
  const devices = fleet?.devices ?? [];

  // Calculate upcoming scheduled exams
  const scheduledExams = exams.filter(e => e.status === 'scheduled');
  const activeExams = exams.filter(e => e.status === 'active');
  const postalExams = exams.filter(e => e.return_type === 'postal' && (e.status === 'scheduled' || e.status === 'active'));
  
  // Calculate booked vs available for current week
  const today = new Date();
  const dayOfWeek = today.getDay();
  const monday = new Date(today);
  monday.setDate(today.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
  const friday = new Date(monday);
  friday.setDate(monday.getDate() + 4);
  
  const thisWeekExams = exams.filter(e => {
    if (!e.scheduled_date || e.status === 'cancelled') return false;
    const d = new Date(e.scheduled_date);
    return d >= monday && d <= friday;
  });
  
  const totalWeekSlots = devices.length * 5; // devices × weekdays
  const bookedSlots = thisWeekExams.length;
  const availableSlots = Math.max(0, totalWeekSlots - bookedSlots);
  const weekUtilization = totalWeekSlots > 0 ? Math.round((bookedSlots / totalWeekSlots) * 100) : 0;

  return (
    <div className="space-y-5 pb-10">

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/25 text-red-300 text-sm">
          <AlertTriangle size={16} className="flex-shrink-0" /> {error}
        </div>
      )}

      {/* Sync status toast */}
      {syncStatus && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-sm animate-pulse">
          <Zap size={16} /> {syncStatus}
          <button onClick={() => setSyncStatus(null)} className="ml-auto text-slate-500 hover:text-slate-300">✕</button>
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiCard icon={BarChart3} label="Veckobeläggning" value={`${weekUtilization}%`}
          sub={`${bookedSlots} / ${totalWeekSlots} slots`} color="pulse" />
        <KpiCard icon={CalendarCheck} label="Bokade" value={bookedSlots} 
          sub="Denna vecka" color="indigo" />
        <KpiCard icon={Cpu} label="Lediga slots" value={availableSlots} 
          sub="Denna vecka" color="emerald" />
        <KpiCard icon={Activity} label="På Patient" value={counts.on_patient ?? 0} 
          sub="Spelar in nu" color="amber" />
        <KpiCard icon={Package} label="Under Post" value={postalExams.length} 
          sub="Postärenden aktiva" color="rose" />
        <KpiCard icon={CalendarCheck} label="Kommande" value={scheduledExams.length} 
          sub={`${activeExams.length} aktiva`} color="teal" />
      </div>

      {/* Fleet grid */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
            <Cpu size={16} className="text-pulse-400" />
            Flotta — live
            <span className="text-xs text-slate-500 font-normal">({devices.length} enheter)</span>
            <span className="relative flex h-2 w-2 ml-1">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
            </span>
          </h2>
          <div className="flex items-center gap-3">
            {lastSync && <span className="text-xs text-slate-600">Uppdaterad {lastSync}</span>}
            <button onClick={load} disabled={refreshing} className="btn-ghost py-1.5 px-3 text-xs">
              <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
              Uppdatera
            </button>
          </div>
        </div>

        <div className="p-5">
          {devices.length === 0 ? (
            <EmptyState refreshing={refreshing} />
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-8 xl:grid-cols-10 gap-2.5">
              {devices.map(d => {
                const meta = STATUS_META[d.status] ?? { label: d.status, dot: 'bg-slate-500', badge: 'bg-slate-700/30 text-slate-400 border-slate-700/50' };
                return (
                  <div key={d.id}
                    className="flex flex-col items-center p-3 rounded-xl bg-slate-50 border border-slate-200 hover:border-pulse-400 hover:shadow-md transition-all duration-150 cursor-pointer group"
                  >
                    <span className={`dot mb-2.5 ${meta.dot}`} />
                    <span className="font-mono text-[11px] font-bold text-slate-700 text-center leading-tight">
                      {d.device_code}
                    </span>
                    <span className={`badge mt-1.5 border text-[9px] ${meta.badge}`}>
                      {meta.label}
                    </span>
                    {d.chain_type && (
                      <span className="mt-1 text-[8px] text-slate-600">
                        {d.chain_type === 'pure_postal' ? '📮' : d.chain_type === 'workhorse' ? '🏥' : '📦'}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function KpiCard({ icon: Icon, label, value, sub, color }) {
  const colorMap = {
    pulse:   { icon: 'text-pulse-400',   bg: 'bg-pulse-500/10' },
    emerald: { icon: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    indigo:  { icon: 'text-indigo-400',  bg: 'bg-indigo-500/10' },
    amber:   { icon: 'text-amber-400',   bg: 'bg-amber-500/10' },
    teal:    { icon: 'text-teal-400',    bg: 'bg-teal-500/10' },
    rose:    { icon: 'text-rose-400',    bg: 'bg-rose-500/10' },
  }[color] ?? { icon: 'text-slate-400',  bg: 'bg-slate-500/10' };

  return (
    <div className="card p-5 flex items-start justify-between gap-4">
      <div>
        <p className="text-[11px] text-slate-400 uppercase tracking-widest font-medium">{label}</p>
        <p className="text-3xl font-bold text-slate-800 mt-1.5">{value}</p>
        <p className="text-xs text-slate-400 mt-1">{sub}</p>
      </div>
      <div className={`p-2.5 rounded-xl ${colorMap.bg} ${colorMap.icon} flex-shrink-0`}>
        <Icon size={20} />
      </div>
    </div>
  );
}

function EmptyState({ refreshing }) {
  return (
    <div className="py-16 text-center">
      {refreshing
        ? <p className="text-slate-500 animate-pulse text-sm">Ansluter till Pulsus Engine…</p>
        : <>
            <p className="text-slate-400 text-sm">Inga enheter registrerade.</p>
            <p className="text-slate-600 text-xs mt-1">Gå till <strong>Enhetsregister</strong> i sidofältet för att lägga till.</p>
          </>
      }
    </div>
  );
}
