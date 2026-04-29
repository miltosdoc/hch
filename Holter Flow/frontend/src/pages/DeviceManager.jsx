import { useState, useEffect, useCallback } from 'react';
import { getFleetStatus, createDevice, deleteDevice, editDevice } from '../services/api';
import { Plus, Trash2, Server, RefreshCw, AlertTriangle, Edit3, Check, X } from 'lucide-react';

const STATUS_META = {
  available:   { label: 'Tillgänglig', style: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  on_patient:  { label: 'På Patient',  style: 'bg-indigo-50  text-indigo-700  border-indigo-200' },
  in_transit:  { label: 'Under Post',  style: 'bg-amber-50   text-amber-700   border-amber-200' },
  returned:    { label: 'Returnerad',  style: 'bg-slate-50   text-slate-600   border-slate-200' },
  maintenance: { label: 'Underhåll',   style: 'bg-rose-50    text-rose-700    border-rose-200' },
  lost:        { label: 'Borttappad',  style: 'bg-red-50     text-red-700     border-red-200' },
  assigned:    { label: 'Tilldelad',   style: 'bg-blue-50    text-blue-700    border-blue-200' },
  processing:  { label: 'Bearbetning', style: 'bg-orange-50  text-orange-700  border-orange-200' },
};

const CHAIN_OPTIONS = [
  { value: '', label: 'Välj typ...' },
  { value: 'workhorse', label: '🏥 Klinik' },
  { value: 'pure_postal', label: '📮 Post' },
  { value: 'postal_72h', label: '📦 72h Post' },
];

const CHAIN_LABELS = {
  workhorse: '🏥 Klinik',
  pure_postal: '📮 Post',
  postal_72h: '📦 72h Post',
};

export default function DeviceManager() {
  const [devices, setDevices] = useState([]);
  const [newCode, setNewCode] = useState('');
  const [newSerial, setNewSerial] = useState('');
  const [newChain, setNewChain] = useState('');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({});

  const loadDevices = useCallback(async () => {
    setRefreshing(true); setError(null);
    try {
      const res = await getFleetStatus();
      setDevices(res.data?.devices ?? []);
    } catch { setError('Backenden är offline — starta Docker.'); }
    finally  { setRefreshing(false); }
  }, []);

  useEffect(() => { loadDevices(); }, [loadDevices]);

  const handleAdd = async e => {
    e.preventDefault();
    const code = newCode.trim();
    if (!code) return;
    setLoading(true); setError(null);
    try {
      await createDevice(code, newSerial.trim() || null, newChain || null);
      setNewCode('');
      setNewSerial('');
      setNewChain('');
      await loadDevices();
    } catch (e) {
      setError(e?.response?.data?.detail ?? 'Kunde inte lägga till enhet. Koden kanske redan finns.');
    } finally { setLoading(false); }
  };

  const handleDelete = async (id, code) => {
    if (!window.confirm(`Ta bort "${code}" permanent?`)) return;
    try { await deleteDevice(id); await loadDevices(); }
    catch { setError('Borttagning misslyckades — enheten kan ha aktiva undersökningar.'); }
  };

  const startEdit = (device) => {
    setEditingId(device.id);
    setEditData({
      device_code: device.device_code,
      serial_number: device.serial_number || '',
      chain_type: device.chain_type || '',
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditData({});
  };

  const saveEdit = async (id) => {
    setError(null);
    try {
      await editDevice(id, editData);
      setEditingId(null);
      setEditData({});
      await loadDevices();
    } catch (e) {
      setError(e?.response?.data?.detail ?? 'Uppdatering misslyckades.');
    }
  };

  return (
    <div className="space-y-5 pb-10 max-w-5xl">
      {error && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
          <AlertTriangle size={16} className="flex-shrink-0" /> {error}
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-2">
            <Server size={16} className="text-pulse-400" />
            <h2 className="text-sm font-semibold text-slate-800">Enhetsregister</h2>
            <span className="text-slate-500 text-xs ml-1">({devices.length} enheter)</span>
          </div>
          <button onClick={loadDevices} disabled={refreshing} className="btn-ghost p-2">
            <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
          </button>
        </div>

        <div className="p-5">
          {/* Add form */}
          <form onSubmit={handleAdd} className="space-y-3 mb-6 p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="text-[11px] text-slate-400 uppercase tracking-widest font-medium mb-2">Lägg till ny enhet</div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <input type="text" value={newCode} onChange={e => setNewCode(e.target.value)}
                placeholder="Enhetskod, t.ex. Cortrium#9"
                className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:border-pulse-400 focus:ring-1 focus:ring-pulse-400/20 transition-colors" />
              <input type="text" value={newSerial} onChange={e => setNewSerial(e.target.value)}
                placeholder="Serienummer (valfritt)"
                className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:border-pulse-400 focus:ring-1 focus:ring-pulse-400/20 transition-colors" />
              <select value={newChain} onChange={e => setNewChain(e.target.value)}
                className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-700 focus:outline-none focus:border-pulse-400 focus:ring-1 focus:ring-pulse-400/20 transition-colors appearance-none">
                {CHAIN_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <button type="submit" disabled={loading || !newCode.trim()} className="btn-primary disabled:opacity-40 w-full sm:w-auto">
              <Plus size={16} />
              {loading ? 'Lägger till…' : 'Lägg till enhet'}
            </button>
          </form>

          {/* Table */}
          {devices.length === 0 ? (
            <div className="py-16 text-center">
              {refreshing
                ? <p className="text-slate-500 animate-pulse text-sm">Laddar enheter…</p>
                : <p className="text-slate-500 text-sm">Inga enheter registrerade ännu.</p>}
            </div>
          ) : (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] text-slate-400 uppercase tracking-widest">
                  <th className="pb-3 px-2 text-left">Kod</th>
                  <th className="pb-3 px-2 text-left">Serienr.</th>
                  <th className="pb-3 px-2 text-left">Status</th>
                  <th className="pb-3 px-2 text-left">Användning</th>
                  <th className="pb-3 px-2 text-right">Åtgärd</th>
                </tr>
              </thead>
              <tbody>
                {devices.map(d => {
                  const meta = STATUS_META[d.status] ?? { label: d.status, style: 'bg-slate-700/30 text-slate-400 border-slate-600/30' };
                  const isEditing = editingId === d.id;

                  return (
                    <tr key={d.id} className="border-b border-slate-100 hover:bg-slate-50 group transition-colors">
                      <td className="py-3 px-2">
                        {isEditing ? (
                          <input type="text" value={editData.device_code}
                            onChange={e => setEditData({...editData, device_code: e.target.value})}
                            className="bg-white border border-pulse-400 rounded-lg px-2 py-1 text-xs text-slate-700 font-mono w-24 focus:outline-none" />
                        ) : (
                          <span className="font-mono font-bold text-slate-700 tracking-wider">{d.device_code}</span>
                        )}
                      </td>
                      <td className="py-3 px-2">
                        {isEditing ? (
                          <input type="text" value={editData.serial_number}
                            onChange={e => setEditData({...editData, serial_number: e.target.value})}
                            placeholder="Serienummer"
                            className="bg-white border border-pulse-400 rounded-lg px-2 py-1 text-xs text-slate-700 font-mono w-28 focus:outline-none" />
                        ) : (
                          <span className="text-slate-500 text-xs font-mono">{d.serial_number || <span className="italic text-slate-300">—</span>}</span>
                        )}
                      </td>
                      <td className="py-3 px-2">
                        <span className={`badge border ${meta.style}`}>{meta.label}</span>
                      </td>
                      <td className="py-3 px-2">
                        {isEditing ? (
                          <select value={editData.chain_type}
                            onChange={e => setEditData({...editData, chain_type: e.target.value})}
                            className="bg-white border border-pulse-400 rounded-lg px-2 py-1 text-xs text-slate-700 focus:outline-none appearance-none">
                            {CHAIN_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                          </select>
                        ) : (
                          <span className="text-xs">
                            {d.chain_type ? <span className="text-slate-600">{CHAIN_LABELS[d.chain_type] || d.chain_type}</span>
                              : <span className="italic text-slate-300">Ej tilldelad</span>}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-2 text-right">
                        {isEditing ? (
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => saveEdit(d.id)}
                              className="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-50 transition-colors">
                              <Check size={14} />
                            </button>
                            <button onClick={cancelEdit}
                              className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-50 transition-colors">
                              <X size={14} />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => startEdit(d)}
                              className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg text-pulse-400 hover:bg-pulse-500/10">
                              <Edit3 size={14} />
                            </button>
                            <button onClick={() => handleDelete(d.id, d.device_code)}
                              className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg text-red-400 hover:bg-red-500/10">
                              <Trash2 size={14} />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
