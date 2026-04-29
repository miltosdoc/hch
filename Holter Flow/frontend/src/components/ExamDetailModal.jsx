import { useState } from 'react';
import { X, Clock, User, Cpu, RefreshCw, AlertTriangle, Trash2, ChevronDown, Package, CheckCircle, LogOut, LogIn, MapPin, RotateCcw, Timer, CalendarPlus } from 'lucide-react';
import { reassignExamDevice, setExamReturnType, setExamDuration, checkoutExam, checkinExam, reactivateExam, postponeExam } from '../services/api';
import MiniCalendar from './MiniCalendar';

const EXAM_LABELS = { '24h': 'Holter 24h', '48h': 'Holter 48h', '72h': 'Holter 72h' };
const STATUS_LABELS = { scheduled: 'Schemalagd', active: 'Aktiv (på patient)', completed: 'Klar', cancelled: 'Avbokad' };
const STATUS_COLORS = {
  scheduled: 'bg-blue-50 text-blue-700 border-blue-200',
  active: 'bg-amber-50 text-amber-700 border-amber-200',
  completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  cancelled: 'bg-slate-50 text-slate-500 border-slate-200',
};

export default function ExamDetailModal({ exam, devices, onClose, onUpdated }) {
  const [reassigning, setReassigning] = useState(false);
  const [selectedDeviceId, setSelectedDeviceId] = useState(exam.device_id);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState(null);
  const [showDeviceDropdown, setShowDeviceDropdown] = useState(false);
  const [returnType, setReturnType] = useState(exam.return_type || 'clinic');
  const [updatingReturn, setUpdatingReturn] = useState(false);
  const [checkingOut, setCheckingOut] = useState(false);
  const [checkingIn, setCheckingIn] = useState(false);
  const [reactivating, setReactivating] = useState(false);
  const [duration, setDuration] = useState(exam.duration_days || {'24h': 1, '48h': 2, '72h': 3}[exam.exam_type] || 1);
  const [updatingDuration, setUpdatingDuration] = useState(false);
  const [postponeDate, setPostponeDate] = useState(new Date().toISOString().split('T')[0]);
  const [postponing, setPostponing] = useState(false);

  const handleReassign = async () => {
    if (selectedDeviceId === exam.device_id) return;
    setReassigning(true); setError(null);
    try {
      await reassignExamDevice(exam.id, selectedDeviceId);
      onUpdated();
    } catch (err) {
      setError('Enhetsbytet misslyckades: ' + (err?.response?.data?.detail || err.message));
    } finally { setReassigning(false); }
  };

  const handleReturnTypeChange = async (newType) => {
    setUpdatingReturn(true); setError(null);
    try {
      await setExamReturnType(exam.id, newType);
      setReturnType(newType);
    } catch (err) {
      setError('Kunde inte ändra returtyp: ' + (err?.response?.data?.detail || err.message));
    } finally { setUpdatingReturn(false); }
  };

  const handleCheckout = async () => {
    if (!window.confirm('Checka ut enheten till patienten? Enheten markeras som "På patient".')) return;
    setCheckingOut(true); setError(null);
    try {
      await checkoutExam(exam.id);
      onUpdated();
    } catch (err) {
      setError('Utcheckning misslyckades: ' + (err?.response?.data?.detail || err.message));
    } finally { setCheckingOut(false); }
  };

  const handleCheckin = async () => {
    if (!window.confirm('Markera enheten som returnerad och tillgänglig?')) return;
    setCheckingIn(true); setError(null);
    try {
      await checkinExam(exam.id);
      onUpdated();
    } catch (err) {
      setError('Incheckning misslyckades: ' + (err?.response?.data?.detail || err.message));
    } finally { setCheckingIn(false); }
  };

  const handleReactivate = async () => {
    if (!window.confirm('Återställ bokningen till schemalagd? Alla tidsdata nollställs.')) return;
    setReactivating(true); setError(null);
    try {
      await reactivateExam(exam.id);
      onUpdated();
    } catch (err) {
      setError('Reaktivering misslyckades: ' + (err?.response?.data?.detail || err.message));
    } finally { setReactivating(false); }
  };

  const handleCancel = async () => {
    if (!window.confirm('Är du säker på att du vill avboka denna undersökning?')) return;
    setCancelling(true); setError(null);
    try {
      const res = await fetch(`/api/v1/webdoc/booking/${exam.id}`, { method: 'DELETE' });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Serverfel vid avbokning');
      }
      onUpdated();
    } catch (err) {
      setError('Avbokning misslyckades: ' + err.message);
    } finally { setCancelling(false); }
  };

  const availableDevices = devices.filter(d => d.id !== exam.device_id);
  const isScheduled = exam.status === 'scheduled';
  const isActive = exam.status === 'active';
  const isCompleted = exam.status === 'completed';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div 
        className="relative bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 sticky top-0 bg-white z-10">
          <h3 className="text-sm font-semibold text-slate-800">Bokningsdetaljer</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {error && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
              <AlertTriangle size={13} /> {error}
            </div>
          )}

          {/* Patient Info */}
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-50 flex items-center justify-center">
                <User size={16} className="text-indigo-600" />
              </div>
              <div>
                <div className="text-sm font-semibold text-slate-800">{exam.patient_name || 'Okänd patient'}</div>
                <div className="text-xs text-slate-400 font-mono">{exam.patient_pn}</div>
                {exam.patient_city && (
                  <div className="text-[10px] text-slate-400 flex items-center gap-0.5 mt-0.5">
                    <MapPin size={8} /> {exam.patient_city}
                  </div>
                )}
              </div>
            </div>

            {/* Status Badge */}
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-[10px] font-semibold border ${STATUS_COLORS[exam.status] || STATUS_COLORS.scheduled}`}>
                {STATUS_LABELS[exam.status] || exam.status}
              </span>
              {returnType === 'postal' && (
                <span className="inline-flex items-center px-2 py-1 rounded-lg text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
                  📮 Postretur
                </span>
              )}
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <div className="text-slate-400 mb-1">Typ</div>
                <div className="text-slate-800 font-semibold">{EXAM_LABELS[exam.exam_type] || exam.exam_type}</div>
                <div className="text-[10px] text-slate-400 mt-0.5">{duration}d mätning</div>
              </div>
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <div className="text-slate-400 mb-1">Datum</div>
                <div className="text-slate-800 font-semibold">{exam.scheduled_date}</div>
              </div>
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <div className="text-slate-400 mb-1 flex items-center gap-1"><Clock size={10} /> Tid</div>
                <div className="text-slate-800 font-semibold">{exam.start_time || '—'}</div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <div className="text-slate-400 mb-1">Åtgärdskod</div>
                <div className="text-slate-800 font-semibold font-mono">{exam.atgardskod || '—'}</div>
              </div>
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <div className="text-slate-400 mb-1">Enhet</div>
                <div className="text-slate-800 font-semibold font-mono text-[10px]">{exam.device_code}</div>
              </div>
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <div className="text-slate-400 mb-1">Utcheckad</div>
                <div className="text-slate-800 font-semibold text-[10px]">
                  {exam.started_at ? new Date(exam.started_at).toLocaleDateString('sv-SE') : '—'}
                </div>
              </div>
            </div>
          </div>

          {/* ═══════════ CHECK-OUT / CHECK-IN BUTTONS ═══════════ */}
          <div className="border-t border-slate-100 pt-4">
            <div className="text-[11px] text-slate-400 uppercase tracking-widest font-medium mb-3 flex items-center gap-1.5">
              <Package size={12} /> Enhetshantering
            </div>

            {isScheduled && (
              <button
                onClick={handleCheckout}
                disabled={checkingOut}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold transition-colors disabled:opacity-40"
              >
                <LogOut size={14} />
                {checkingOut ? 'Checkar ut…' : 'Checka ut till patient'}
              </button>
            )}

            {isActive && (
              <div className="space-y-3">
                <button
                  onClick={handleCheckin}
                  disabled={checkingIn}
                  className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition-colors disabled:opacity-40"
                >
                  <LogIn size={14} />
                  {checkingIn ? 'Checkar in…' : 'Checka in enhet (returnerad)'}
                </button>
                
                {/* Postpone return */}
                <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                  <div className="text-[10px] text-slate-400 uppercase tracking-widest font-medium mb-2 flex items-center gap-1">
                    <CalendarPlus size={10} /> Skjut upp inlämning
                  </div>
                  {exam.expected_return_at && (
                    <p className="text-[10px] text-slate-500 mb-2">
                      Nuvarande returdatum: <strong>{exam.expected_return_at.split('T')[0]}</strong>
                    </p>
                  )}
                  <MiniCalendar
                    selectedDate={postponeDate}
                    onSelect={(d) => setPostponeDate(d)}
                    minDate={new Date().toISOString().split('T')[0]}
                  />
                  <button
                    disabled={!postponeDate || postponing}
                    onClick={async () => {
                      setPostponing(true); setError(null);
                      try {
                        await postponeExam(exam.id, postponeDate);
                        onUpdated();
                      } catch (err) {
                        setError('Kunde inte skjuta upp: ' + (err?.response?.data?.detail || err.message));
                      } finally { setPostponing(false); }
                    }}
                    className="w-full mt-2 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold transition-colors disabled:opacity-30"
                  >
                    {postponing ? 'Sparar…' : `Bekräfta nytt datum: ${postponeDate}`}
                  </button>
                </div>
              </div>
            )}

            {isCompleted && (
              <div className="space-y-2">
                <div className="flex items-center justify-center gap-2 py-3 rounded-xl bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-200">
                  <CheckCircle size={14} />
                  Returnerad {exam.actual_return_at ? new Date(exam.actual_return_at).toLocaleDateString('sv-SE') : ''}
                </div>
                <button
                  onClick={handleReactivate}
                  disabled={reactivating}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-amber-200 bg-amber-50 text-amber-700 text-xs font-medium hover:bg-amber-100 transition-colors disabled:opacity-40"
                >
                  <RotateCcw size={13} className={reactivating ? 'animate-spin' : ''} />
                  {reactivating ? 'Återställer…' : 'Reaktivera bokning'}
                </button>
              </div>
            )}
          </div>
          {/* Duration Selector (for all scheduled exams) */}
          {isScheduled && (
            <div className="border-t border-slate-100 pt-4">
              <div className="text-[11px] text-slate-400 uppercase tracking-widest font-medium mb-3 flex items-center gap-1.5">
                <Timer size={12} /> Mätdagar
              </div>
              <div className="flex items-center gap-1.5">
                {[1, 2, 3, 4, 5, 6, 7].map(d => (
                  <button
                    key={d}
                    disabled={updatingDuration}
                    onClick={async () => {
                      setUpdatingDuration(true);
                      try {
                        await setExamDuration(exam.id, d);
                        setDuration(d);
                      } catch (err) {
                        setError('Kunde inte ändra mätdagar: ' + (err?.response?.data?.detail || err.message));
                      } finally { setUpdatingDuration(false); }
                    }}
                    className={`flex-1 py-2 rounded-lg text-xs font-semibold transition-all
                      ${duration === d 
                        ? 'bg-indigo-600 text-white shadow-sm' 
                        : 'bg-slate-50 text-slate-500 border border-slate-100 hover:border-indigo-200 hover:text-indigo-600'}`}
                  >
                    {d}d
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-slate-400 mt-2">
                Webdoc-typ: {EXAM_LABELS[exam.exam_type] || exam.exam_type} · Faktisk mätning: <strong>{duration} dagar</strong>
              </p>
            </div>
          )}


          {/* Return Type Toggle (only for scheduled exams) */}
          {isScheduled && (
            <div className="border-t border-slate-100 pt-4">
              <div className="text-[11px] text-slate-400 uppercase tracking-widest font-medium mb-3 flex items-center gap-1.5">
                📮 Returmetod
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleReturnTypeChange('clinic')}
                  disabled={updatingReturn}
                  className={`py-2.5 px-3 rounded-xl text-xs font-medium transition-all flex items-center justify-center gap-2
                    ${returnType === 'clinic' 
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-300 ring-1 ring-emerald-200' 
                      : 'bg-slate-50 text-slate-500 border border-slate-100 hover:border-slate-300'}`}
                >
                  🏥 Fysiskt besök
                </button>
                <button
                  onClick={() => handleReturnTypeChange('postal')}
                  disabled={updatingReturn}
                  className={`py-2.5 px-3 rounded-xl text-xs font-medium transition-all flex items-center justify-center gap-2
                    ${returnType === 'postal' 
                      ? 'bg-amber-50 text-amber-700 border border-amber-300 ring-1 ring-amber-200' 
                      : 'bg-slate-50 text-slate-500 border border-slate-100 hover:border-slate-300'}`}
                >
                  📮 Postretur
                </button>
              </div>
              {returnType === 'postal' && (
                <p className="text-[10px] text-slate-400 mt-2">Patienten hämtar enheten här. Returnerar via post (+3 vardagar transit).</p>
              )}
            </div>
          )}

          {/* Device Reassignment (only for scheduled exams) */}
          {isScheduled && (
            <div className="border-t border-slate-100 pt-4">
              <div className="text-[11px] text-slate-400 uppercase tracking-widest font-medium mb-3 flex items-center gap-1.5">
                <Cpu size={12} /> Byt Enhet
              </div>
              
              <div className="flex items-center gap-3">
                <div className="relative flex-1">
                  <button 
                    onClick={() => setShowDeviceDropdown(!showDeviceDropdown)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-700 flex items-center justify-between hover:border-indigo-300 transition-colors"
                  >
                    <span className="font-mono text-xs">
                      {devices.find(d => d.id === selectedDeviceId)?.device_code || exam.device_code}
                    </span>
                    <ChevronDown size={14} className="text-slate-400" />
                  </button>

                  {showDeviceDropdown && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-2xl max-h-48 overflow-y-auto z-10">
                      {availableDevices.map(d => (
                        <button
                          key={d.id}
                          onClick={() => { setSelectedDeviceId(d.id); setShowDeviceDropdown(false); }}
                          className="w-full text-left px-4 py-2 text-xs hover:bg-indigo-50 transition-colors flex items-center justify-between"
                        >
                          <span className="font-mono text-slate-700">{d.device_code}</span>
                          <span className="text-slate-400 text-[10px]">
                            {d.status === 'available' ? '🟢' : d.status === 'on_patient' ? '🔴' : '🟡'}
                          </span>
                        </button>
                      ))}
                      {availableDevices.length === 0 && (
                        <div className="px-4 py-3 text-xs text-slate-400">Inga andra enheter</div>
                      )}
                    </div>
                  )}
                </div>
                
                <button
                  onClick={handleReassign}
                  disabled={reassigning || selectedDeviceId === exam.device_id}
                  className="btn-primary py-2 px-4 text-xs disabled:opacity-30"
                >
                  <RefreshCw size={13} className={reassigning ? 'animate-spin' : ''} />
                  Byt
                </button>
              </div>
            </div>
          )}

          {/* Cancel (only for scheduled) */}
          {isScheduled && (
            <div className="border-t border-slate-100 pt-4">
              <button
                onClick={handleCancel}
                disabled={cancelling}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-red-200 bg-red-50 text-red-600 text-xs font-medium hover:bg-red-100 transition-colors disabled:opacity-40"
              >
                <Trash2 size={13} />
                {cancelling ? 'Avbokar…' : 'Avboka i Webdoc & Pulsus'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
