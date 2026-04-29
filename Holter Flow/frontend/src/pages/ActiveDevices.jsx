import { useState, useEffect } from 'react';
import { Activity, CheckCircle, Clock, MapPin, AlertTriangle, Cpu, CalendarPlus } from 'lucide-react';
import { getActiveClinic, checkinExam, postponeExam } from '../services/api';
import MiniCalendar from '../components/MiniCalendar';

export default function ActiveDevices() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [postponeId, setPostponeId] = useState(null);
  const [postponeDate, setPostponeDate] = useState(new Date().toISOString().split('T')[0]);
  const [postponing, setPostponing] = useState(false);

  const fetchData = async () => {
    try {
      const res = await getActiveClinic();
      if (Array.isArray(res.data)) setDevices(res.data);
    } catch (err) {
      console.error('Failed to fetch active clinic devices', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleCheckin = async (examId) => {
    if (!window.confirm('Markera enheten som returnerad och tillgänglig?')) return;
    try {
      await checkinExam(examId);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handlePostpone = async (examId) => {
    if (!postponeDate) return;
    setPostponing(true);
    try {
      await postponeExam(examId, postponeDate);
      setPostponeId(null);
      setPostponeDate('');
      fetchData();
    } catch (err) {
      console.error(err);
      alert('Kunde inte skjuta upp: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setPostponing(false);
    }
  };

  const isOverdue = (expectedReturn) => {
    if (!expectedReturn) return false;
    return new Date() > new Date(expectedReturn);
  };

  return (
    <div className="max-w-6xl mx-auto pb-12 space-y-5">
      <div className="mb-2">
        <h1 className="text-xl font-bold text-slate-800 mb-1">Utcheckade Enheter</h1>
        <p className="text-slate-500 text-sm">
          Enheter som är utcheckade till patienter för klinikbesök. Checka in när patienten returnerar enheten.
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="card p-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] text-slate-400 uppercase tracking-widest font-medium">Utcheckade nu</p>
            <p className="text-3xl font-bold text-slate-800 mt-1.5">{devices.length}</p>
            <p className="text-xs text-slate-400 mt-1">Enheter på patient</p>
          </div>
          <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-500 flex-shrink-0">
            <Activity size={18} />
          </div>
        </div>

        <div className="card p-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] text-slate-400 uppercase tracking-widest font-medium">Försenade</p>
            <p className="text-3xl font-bold text-slate-800 mt-1.5">
              {devices.filter(d => isOverdue(d.expected_return_at)).length}
            </p>
            <p className="text-xs text-slate-400 mt-1">Passerat förväntat returdatum</p>
          </div>
          <div className="p-2.5 rounded-xl bg-red-50 text-red-500 flex-shrink-0">
            <AlertTriangle size={18} />
          </div>
        </div>

        <div className="card p-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] text-slate-400 uppercase tracking-widest font-medium">Nästa retur</p>
            <p className="text-lg font-bold text-slate-800 mt-1.5">
              {devices.length > 0 
                ? devices
                    .filter(d => d.expected_return_at)
                    .sort((a, b) => new Date(a.expected_return_at) - new Date(b.expected_return_at))[0]
                    ?.expected_return_at?.split('T')[0] || '—'
                : '—'}
            </p>
            <p className="text-xs text-slate-400 mt-1">Tidigast förväntat</p>
          </div>
          <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-500 flex-shrink-0">
            <Clock size={18} />
          </div>
        </div>
      </div>

      {/* Active Devices Table */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
            <Cpu size={16} className="text-indigo-500" />
            Enheter på patient
            <span className="text-xs text-slate-500 font-normal">({devices.length} st)</span>
          </h2>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400 animate-pulse">Laddar data...</div>
        ) : devices.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 rounded-full bg-emerald-50 flex items-center justify-center mb-4">
              <CheckCircle size={32} className="text-emerald-400" />
            </div>
            <p className="text-slate-600 font-medium text-lg">Alla enheter tillgängliga</p>
            <p className="text-slate-400 mt-1 text-sm">Inga enheter är utcheckade just nu.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] text-slate-400 uppercase tracking-wider">
                  <th className="py-4 px-5 font-medium">Enhet</th>
                  <th className="py-4 px-5 font-medium">Patient</th>
                  <th className="py-4 px-5 font-medium">Typ</th>
                  <th className="py-4 px-5 font-medium">Utcheckad</th>
                  <th className="py-4 px-5 font-medium">Förväntas tillbaka</th>
                  <th className="py-4 px-5 font-medium">Status</th>
                  <th className="py-4 px-5 font-medium text-right">Åtgärd</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {devices.map((d) => {
                  const overdue = isOverdue(d.expected_return_at);
                  const isPostponing = postponeId === d.exam_id;

                  return (
                    <tr key={d.exam_id} className={`transition-colors ${overdue ? 'bg-red-50' : 'hover:bg-slate-50'}`}>
                      <td className="py-4 px-5">
                        <div className="font-mono font-bold text-slate-700 text-xs">{d.device_code}</div>
                      </td>
                      <td className="py-4 px-5">
                        <div className="text-slate-700 text-xs font-medium">{d.patient_name}</div>
                        <div className="text-slate-400 text-[10px] font-mono">{d.patient_pn}</div>
                        {d.patient_city && (
                          <div className="text-[9px] text-slate-400 flex items-center gap-0.5 mt-0.5">
                            <MapPin size={7} /> {d.patient_city}
                          </div>
                        )}
                      </td>
                      <td className="py-4 px-5">
                        <span className="text-xs text-slate-600">{d.exam_type}</span>
                        <div className="text-[10px] text-slate-400">{d.duration_days}d mätning</div>
                      </td>
                      <td className="py-4 px-5">
                        <div className="text-xs text-slate-700">
                          {d.started_at ? new Date(d.started_at).toLocaleDateString('sv-SE') : '—'}
                        </div>
                      </td>
                      <td className="py-4 px-5">
                        {d.expected_return_at ? (
                          <div className={`text-xs font-medium ${overdue ? 'text-red-600' : 'text-slate-700'}`}>
                            {d.expected_return_at.split('T')[0]}
                            {overdue && <span className="ml-1.5 text-[9px] text-red-400">(försenad)</span>}
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                        {/* Inline postpone calendar */}
                        {isPostponing && (
                          <div className="mt-2">
                            <MiniCalendar
                              selectedDate={postponeDate}
                              onSelect={(d) => setPostponeDate(d)}
                              minDate={new Date().toISOString().split('T')[0]}
                            />
                            <div className="flex items-center gap-1.5 mt-1.5">
                              <button
                                disabled={!postponeDate || postponing}
                                onClick={() => handlePostpone(d.exam_id)}
                                className="flex-1 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-[10px] font-semibold disabled:opacity-30"
                              >
                                {postponing ? '…' : `Bekräfta: ${postponeDate}`}
                              </button>
                              <button
                                onClick={() => { setPostponeId(null); }}
                                className="px-2 py-1.5 rounded-lg text-[10px] text-slate-400 hover:text-slate-600 border border-slate-200"
                              >
                                Avbryt
                              </button>
                            </div>
                          </div>
                        )}
                      </td>
                      <td className="py-4 px-5">
                        <div className="flex items-center gap-2">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-medium ${
                            overdue 
                              ? 'bg-red-50 text-red-600 border border-red-200' 
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}>
                            <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                            På patient
                          </span>
                          <span className={`text-[10px] ${overdue ? 'text-red-600 font-semibold' : 'text-slate-500'}`}>
                            {d.days_out}d
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => { setPostponeId(isPostponing ? null : d.exam_id); setPostponeDate(new Date().toISOString().split('T')[0]); }}
                            title="Skjut upp inlämning"
                            className="bg-amber-50 hover:bg-amber-100 text-amber-600 border border-amber-200 px-2.5 py-1.5 rounded-lg text-[10px] font-medium transition-colors inline-flex items-center gap-1"
                          >
                            <CalendarPlus size={11} /> Skjut upp
                          </button>
                          <button
                            onClick={() => handleCheckin(d.exam_id)}
                            className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-[10px] font-medium transition-colors inline-flex items-center gap-1.5"
                          >
                            <CheckCircle size={12} /> Checka in
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
