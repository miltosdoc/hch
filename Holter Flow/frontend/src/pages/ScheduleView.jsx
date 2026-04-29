import { useState, useEffect, useCallback } from 'react';
import { getFleetStatus, fetchExams, syncWebdocExams, getRevenueSuggestions } from '../services/api';
import { Calendar, RefreshCw, ChevronLeft, ChevronRight, AlertTriangle, TrendingUp, Zap, Clock, MapPin } from 'lucide-react';

import BookingModal from '../components/BookingModal';
import ExamDetailModal from '../components/ExamDetailModal';

const DAYS_SV = ['Måndag', 'Tisdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lördag', 'Söndag'];

function getWeekDates(offset = 0) {
  const today = new Date();
  const day = today.getDay();
  const diffToMon = (day === 0 ? -6 : 1 - day) + offset * 7;
  const monday = new Date(today);
  monday.setDate(today.getDate() + diffToMon);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d;
  });
}

const fmt = d => d.toISOString().split('T')[0];
const todayStr = fmt(new Date());

const EXAM_TYPE_STYLE = {
  '24h': 'bg-indigo-50 border-indigo-200 text-indigo-800',
  '48h': 'bg-teal-50 border-teal-200 text-teal-800',
  '72h': 'bg-amber-50 border-amber-200 text-amber-800',
};

export default function ScheduleView() {
  const [devices, setDevices] = useState([]);
  const [exams,   setExams]   = useState([]);
  const [offset,  setOffset]  = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const [showBookingModal, setShowBookingModal] = useState(false);
  const [selectedExam, setSelectedExam] = useState(null);
  const [suggestions, setSuggestions] = useState(null);

  const weekDates = getWeekDates(offset);
  const weekLabel = `v.${getISOWeek(weekDates[0])} · ${fmt(weekDates[0])} — ${fmt(weekDates[6])}`;

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [dr, er] = await Promise.all([getFleetStatus(), fetchExams()]);
      setDevices(dr.data?.devices ?? []);
      setExams(er.data ?? []);
    } catch { setError('Backenden är offline — starta Docker under port 8080.'); }
    finally  { setLoading(false); }
  }, []);

  const loadSuggestions = useCallback(async () => {
    try {
      const res = await getRevenueSuggestions();
      setSuggestions(res.data);
    } catch { /* silent */ }
  }, []);

  useEffect(() => { load(); loadSuggestions(); }, [load, loadSuggestions]);
  
  // Auto-refresh every 30 seconds
  useEffect(() => {
    const t = setInterval(() => { load(); loadSuggestions(); }, 30_000);
    return () => clearInterval(t);
  }, [load, loadSuggestions]);

  const handleSync = async () => {
    setSyncing(true);
    try { await syncWebdocExams(); await load(); await loadSuggestions(); }
    catch { setError('Webdoc-synk misslyckades.'); }
    finally { setSyncing(false); }
  };

  return (
    <div className="space-y-4 pb-10 relative">
      {showBookingModal && (
        <BookingModal 
           onClose={() => setShowBookingModal(false)}
           targetDate={fmt(weekDates[0])}
           onBookingSuccess={() => { setShowBookingModal(false); load(); loadSuggestions(); }}
        />
      )}

      {selectedExam && (
        <ExamDetailModal
          exam={selectedExam}
          devices={devices}
          onClose={() => setSelectedExam(null)}
          onUpdated={() => { setSelectedExam(null); load(); loadSuggestions(); }}
        />
      )}

      {error && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      <div className="card">
        {/* Header */}
        <div className="card-header flex-wrap gap-3">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <Calendar size={17} className="text-pulse-400" />
            <h2 className="text-sm font-semibold text-slate-800">Veckoschema</h2>
            <span className="text-slate-500 text-xs hidden md:inline">{weekLabel}</span>
          </div>
          
          <div className="flex-1 flex justify-end">
            <button 
              onClick={() => setShowBookingModal(true)} 
              className="bg-pulse-500 hover:bg-pulse-600 text-white font-medium text-xs px-4 py-2 rounded-lg shadow-lg transition-transform hover:scale-105 mr-4"
            >
              + Ny Bokning
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={() => setOffset(o => o - 1)} className="btn-ghost p-2">
              <ChevronLeft size={15} />
            </button>
            <button onClick={() => setOffset(0)} className="btn-ghost text-xs px-3 py-1.5">Idag</button>
            <button onClick={() => setOffset(o => o + 1)} className="btn-ghost p-2">
              <ChevronRight size={15} />
            </button>
            <button onClick={handleSync} disabled={syncing} className="btn-primary py-1.5 px-3 text-xs">
              <RefreshCw size={13} className={syncing ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">{syncing ? 'Synkar…' : 'Sync Webdoc'}</span>
            </button>
          </div>
        </div>

        {/* Grid */}
        <div className="p-4 overflow-x-auto">
          <table className="w-full border-collapse min-w-[860px] text-xs">
            <thead>
              <tr>
                <th className="py-3 px-3 text-left text-[11px] text-slate-400 uppercase tracking-widest w-28 border-b border-r border-slate-100">
                  Enhet
                </th>
                {weekDates.map((d, i) => {
                  const isToday = fmt(d) === todayStr;
                  return (
                    <th key={i} className={`py-3 px-2 text-center border-b border-r border-slate-100
                      ${isToday ? 'bg-indigo-50/50' : ''}`}>
                      <div className={`text-[10px] uppercase tracking-widest font-medium ${isToday ? 'text-pulse-500' : 'text-slate-400'}`}>
                        {DAYS_SV[i].slice(0, 3)}
                      </div>
                      <div className={`text-xl font-bold mt-0.5 ${isToday ? 'text-pulse-600' : 'text-slate-700'}`}>
                        {d.getDate()}
                      </div>
                      <div className="text-[9px] text-slate-400 mt-0.5">
                        {d.toLocaleDateString('sv-SE', { month: 'short' })}
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {devices.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-16 text-center text-slate-600">
                    {loading
                      ? <span className="animate-pulse">Laddar enheter…</span>
                      : 'Inga enheter. Lägg till via Enhetsregister.'}
                  </td>
                </tr>
              ) : devices.map(device => (
                <tr key={device.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-2 px-3 border-r border-slate-100 align-top">
                    <div className="font-mono font-bold text-slate-700 text-[11px]">{device.device_code}</div>
                    {device.serial_number && (
                      <div className="text-[8px] text-slate-600 mt-0.5 font-mono">{device.serial_number}</div>
                    )}
                    {device.chain_type && (
                      <div className="text-[9px] text-slate-600 mt-0.5 capitalize">
                        {device.chain_type === 'pure_postal' ? '📮 Post' : device.chain_type === 'workhorse' ? '🏥 Klinik' : device.chain_type.replace('_', ' ')}
                      </div>
                    )}
                  </td>
                  {weekDates.map((d, di) => {
                    const dateStr   = fmt(d);
                    const isToday   = dateStr === todayStr;
                    const dayExams  = exams.filter(e => e.device_id === device.id && e.scheduled_date === dateStr && e.status !== 'cancelled');
                    return (
                      <td key={di}
                        className={`p-1 border-r border-slate-100 min-w-[100px] align-top
                          ${isToday ? 'bg-indigo-50/30' : ''}`}
                      >
                        {dayExams.map(ex => (
                          <div key={ex.id}
                            title="Klicka för detaljer"
                            onClick={() => setSelectedExam(ex)}
                            className={`rounded-lg border px-2 py-1.5 mb-1 leading-tight cursor-pointer hover:ring-1 hover:ring-pulse-400 hover:shadow-sm transition-all
                              ${EXAM_TYPE_STYLE[ex.exam_type] ?? 'bg-slate-50 border-slate-200 text-slate-700'}`}
                          >
                            <div className="font-semibold truncate text-[11px] flex items-center gap-1">
                              {ex.status === 'active' && <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse flex-shrink-0" title="På patient" />}
                              {ex.status === 'completed' && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" title="Returnerad" />}
                              {ex.patient_name || "Okänd"}
                            </div>
                            <div className="flex items-center gap-1.5 text-[9px] opacity-70 mt-0.5">
                              {ex.start_time && (
                                <span className="flex items-center gap-0.5">
                                  <Clock size={8} /> {ex.start_time}
                                </span>
                              )}
                              <span>{ex.duration_days && ex.duration_days !== {'24h':1,'48h':2,'72h':3}[ex.exam_type] ? `${ex.duration_days}d` : ex.exam_type}</span>
                              {ex.return_type === 'postal' && <span title="Postretur">📮</span>}
                            </div>
                            {ex.patient_city && (
                              <div className="flex items-center gap-0.5 text-[8px] opacity-60 mt-0.5 truncate">
                                <MapPin size={7} /> {ex.patient_city}
                              </div>
                            )}
                            {ex.status === 'active' && ex.expected_return_at && (
                              <div className="text-[8px] mt-0.5 text-amber-700 font-medium">
                                ↩ Retur: {ex.expected_return_at.split('T')[0]}
                              </div>
                            )}
                          </div>
                        ))}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div className="px-4 pb-4 flex gap-5 text-[10px] text-slate-500">
          {Object.entries(EXAM_TYPE_STYLE).map(([t, cls]) => (
            <div key={t} className="flex items-center gap-1.5">
              <div className={`w-2.5 h-2.5 rounded-sm border ${cls}`} />
              {t} Holter
            </div>
          ))}
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-sm bg-pulse-500/[0.04] border border-pulse-400/15" />
            Idag
          </div>
        </div>
      </div>

      {/* Revenue Suggestions Panel */}
      {suggestions && suggestions.suggestions?.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div className="flex items-center gap-2">
              <TrendingUp size={16} className="text-emerald-600" />
              <h2 className="text-sm font-semibold text-slate-800">Föreslagna Bokningar</h2>
              <span className="text-slate-400 text-xs">Optimerad för intäkt</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap size={13} className="text-amber-500" />
              <span className="text-xs text-amber-700 font-semibold">
                Potentiell intäkt: {suggestions.total_potential_sek?.toLocaleString('sv-SE')} SEK
              </span>
            </div>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {suggestions.suggestions.map((s, idx) => (
                <div key={idx} className="bg-slate-50 rounded-xl border border-slate-200 p-4 hover:border-emerald-400 hover:shadow-sm transition-colors group">
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-md border ${EXAM_TYPE_STYLE[s.exam_type] || 'text-slate-600'}`}>
                      {s.exam_type} Holter
                    </span>
                    <span className="text-emerald-600 font-bold text-sm">{s.revenue_sek?.toLocaleString('sv-SE')} kr</span>
                  </div>
                  <div className="text-xs text-slate-500 space-y-1">
                    <div className="flex justify-between">
                      <span>Datum</span>
                      <span className="text-slate-700 font-medium">{s.date}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Tid</span>
                      <span className="text-slate-700 font-medium">{s.time}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Enhet</span>
                      <span className="text-slate-700 font-mono text-[10px]">{s.device_code}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Lediga enheter</span>
                      <span className="text-emerald-600 font-medium">{s.available_devices}</span>
                    </div>
                  </div>
                  <button 
                    onClick={() => setShowBookingModal(true)}
                    className="mt-3 w-full text-center text-[10px] py-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-emerald-100"
                  >
                    Boka direkt →
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function getISOWeek(date) {
  const d = new Date(date);
  d.setHours(0,0,0,0);
  d.setDate(d.getDate() + 4 - (d.getDay() || 7));
  const y = new Date(d.getFullYear(), 0, 1);
  return Math.ceil((((d - y) / 86400000) + 1) / 7);
}
