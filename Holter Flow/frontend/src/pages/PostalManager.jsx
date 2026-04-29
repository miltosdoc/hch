import { useState, useEffect } from 'react';
import { PackageX, Mail, CheckCircle, PackageSearch, AlertTriangle, BarChart3, Clock, TrendingDown, TrendingUp } from 'lucide-react';
import { getPostalActive, getPostalStats, markPostalTransit, markPostalReceived } from '../services/api';

export default function PostalManager() {
  const [packages, setPackages] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchAll = async () => {
    try {
      const [pkgRes, statsRes] = await Promise.all([getPostalActive(), getPostalStats()]);
      if (Array.isArray(pkgRes.data)) setPackages(pkgRes.data);
      setStats(statsRes.data);
    } catch (err) {
      console.error('Failed to fetch postal data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleMarkTransit = async (examId) => {
    try {
      await markPostalTransit(examId);
      fetchAll();
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkReceived = async (examId) => {
    try {
      await markPostalReceived(examId);
      fetchAll();
    } catch (err) {
      console.error(err);
    }
  };

  const isOverdue = (estimatedArrival) => {
    if (!estimatedArrival) return false;
    return new Date() > new Date(estimatedArrival);
  };

  return (
    <div className="max-w-6xl mx-auto pb-12 space-y-5">
      <div className="mb-2">
        <h1 className="text-xl font-bold text-slate-800 mb-1">Posthantering</h1>
        <p className="text-slate-500 text-sm">
          Spåra enheter som returneras via post. Patienten hämtar enheten på kliniken men skickar tillbaka den per post (+3 vardagar transit).
        </p>
      </div>

      {/* Postal Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            icon={BarChart3} 
            label="Slutförda" 
            value={stats.total_completed} 
            sub="Postärenden totalt"
            color="pulse" 
          />
          <StatCard 
            icon={Clock} 
            label="Median transit" 
            value={`${stats.median_transit_days} d`} 
            sub="Baserat på historik"
            color="amber" 
          />
          <StatCard 
            icon={TrendingDown} 
            label="Snabbast" 
            value={stats.min_days !== null ? `${stats.min_days} d` : '—'} 
            sub="Minsta returtid"
            color="emerald" 
          />
          <StatCard 
            icon={TrendingUp} 
            label="Långsammast" 
            value={stats.max_days !== null ? `${stats.max_days} d` : '—'} 
            sub="Längsta returtid"
            color="rose" 
          />
        </div>
      )}

      {/* Transit Time Sparkline */}
      {stats?.transit_times?.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
              <BarChart3 size={14} className="text-pulse-400" />
              Transithistorik
            </h2>
            <span className="text-xs text-slate-500">Senaste {stats.transit_times.length} returer</span>
          </div>
          <div className="p-4">
            <div className="flex items-end gap-1 h-16">
              {stats.transit_times.map((days, i) => {
                const maxDays = Math.max(...stats.transit_times, 1);
                const height = Math.max((days / maxDays) * 100, 8);
                const isHigh = days > stats.median_transit_days;
                return (
                  <div
                    key={i}
                    title={`${days} dagar`}
                    className={`flex-1 rounded-t transition-all ${isHigh ? 'bg-amber-300' : 'bg-indigo-300'}`}
                    style={{ height: `${height}%` }}
                  />
                );
              })}
            </div>
            <div className="flex justify-between mt-1 text-[9px] text-slate-600">
              <span>Äldsta</span>
              <span className="text-amber-600">Median: {stats.median_transit_days} dagar</span>
              <span>Senaste</span>
            </div>
          </div>
        </div>
      )}

      {/* Active Postal Packages Table */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
            <PackageSearch size={16} className="text-amber-500" />
            Aktiva Postärenden
            <span className="text-xs text-slate-500 font-normal">({packages.length} ärenden)</span>
          </h2>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400 animate-pulse">Laddar data...</div>
        ) : packages.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
              <PackageX size={32} className="text-slate-400" />
            </div>
            <p className="text-slate-600 font-medium text-lg">Inga aktiva postärenden</p>
            <p className="text-slate-400 mt-1 text-sm">Alla utskickade enheter är mottagna eller åter på kliniken.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] text-slate-400 uppercase tracking-wider">
                  <th className="py-4 px-5 font-medium">Enhet</th>
                  <th className="py-4 px-5 font-medium">Patient</th>
                  <th className="py-4 px-5 font-medium">Typ</th>
                  <th className="py-4 px-5 font-medium">Skickad</th>
                  <th className="py-4 px-5 font-medium">Beräknad ankomst</th>
                  <th className="py-4 px-5 font-medium">Status</th>
                  <th className="py-4 px-5 font-medium text-right">Åtgärd</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {packages.map((pkg) => {
                  const overdue = isOverdue(pkg.estimated_arrival);

                  return (
                    <tr key={pkg.exam_id} className={`transition-colors ${overdue ? 'bg-red-50' : 'hover:bg-slate-50'}`}>
                      <td className="py-4 px-5">
                        <div className="font-mono font-bold text-slate-700 text-xs">{pkg.device_code}</div>
                      </td>
                      <td className="py-4 px-5">
                        <div className="text-slate-700 text-xs">{pkg.patient_name}</div>
                        <div className="text-slate-400 text-[10px] font-mono">{pkg.patient_pn}</div>
                      </td>
                      <td className="py-4 px-5">
                        <span className="text-xs text-slate-400">{pkg.exam_type}</span>
                      </td>
                      <td className="py-4 px-5">
                        <div className="text-xs text-slate-300">{pkg.scheduled_date || '—'}</div>
                        {pkg.start_time && <div className="text-[10px] text-slate-600">kl {pkg.start_time}</div>}
                      </td>
                      <td className="py-4 px-5">
                        {pkg.estimated_arrival ? (
                          <div className={`text-xs font-medium ${overdue ? 'text-red-600' : 'text-slate-700'}`}>
                            {pkg.estimated_arrival}
                            {overdue && <span className="ml-1.5 text-[9px] text-red-400">(försenad)</span>}
                          </div>
                        ) : (
                          <span className="text-xs text-slate-600">—</span>
                        )}
                      </td>
                      <td className="py-4 px-5">
                        {pkg.device_status === 'available' || pkg.device_status === 'assigned' ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-medium bg-slate-100 text-slate-500 border border-slate-200">
                            Väntar på utcheckning
                          </span>
                        ) : pkg.device_status === 'on_patient' ? (
                          <div className="flex items-center gap-2">
                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-medium ${overdue ? 'bg-red-50 text-red-600 border border-red-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}>
                              📦 På patient
                            </span>
                            {overdue && <AlertTriangle size={12} className="text-red-500" />}
                            <span className={`text-[10px] ${overdue ? 'text-red-600 font-semibold' : 'text-slate-500'}`}>
                              {pkg.days_in_transit}d
                            </span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-medium ${overdue ? 'bg-red-50 text-red-600 border border-red-200' : 'bg-blue-50 text-blue-700 border border-blue-200'}`}>
                              📮 I postretur
                            </span>
                            {overdue && <AlertTriangle size={12} className="text-red-500" />}
                            <span className={`text-[10px] ${overdue ? 'text-red-600 font-semibold' : 'text-slate-500'}`}>
                              {pkg.days_in_transit}d
                            </span>
                          </div>
                        )}
                      </td>
                      <td className="py-4 px-5 text-right">
                        {pkg.device_status === 'available' || pkg.device_status === 'assigned' ? (
                          <span className="text-[10px] text-slate-400 italic">Checka ut via Veckoschema</span>
                        ) : (
                          <button
                            onClick={() => handleMarkReceived(pkg.exam_id)}
                            className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-[10px] font-medium transition-colors inline-flex items-center gap-1.5"
                          >
                            <CheckCircle size={12} /> Checka in (mottagen)
                          </button>
                        )}
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

function StatCard({ icon: Icon, label, value, sub, color }) {
  const colorMap = {
    pulse:   { icon: 'text-pulse-400',   bg: 'bg-pulse-500/10' },
    emerald: { icon: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    amber:   { icon: 'text-amber-400',   bg: 'bg-amber-500/10' },
    rose:    { icon: 'text-rose-400',    bg: 'bg-rose-500/10' },
  }[color] ?? { icon: 'text-slate-400',  bg: 'bg-slate-500/10' };

  return (
    <div className="card p-5 flex items-start justify-between gap-4">
      <div>
        <p className="text-[11px] text-slate-400 uppercase tracking-widest font-medium">{label}</p>
        <p className="text-2xl font-bold text-slate-800 mt-1.5">{value}</p>
        <p className="text-xs text-slate-400 mt-1">{sub}</p>
      </div>
      <div className={`p-2.5 rounded-xl ${colorMap.bg} ${colorMap.icon} flex-shrink-0`}>
        <Icon size={18} />
      </div>
    </div>
  );
}
