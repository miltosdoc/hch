import { useState, useEffect } from 'react';
import { Calendar, User, Clock, ChevronRight, CheckCircle, Package, AlertTriangle, X, ArrowLeft } from 'lucide-react';

export default function BookingModal({ onClose, targetDate, onBookingSuccess }) {
  const [step, setStep] = useState(1);
  const [duration, setDuration] = useState('24h');
  const [customDays, setCustomDays] = useState(1);
  const [slots, setSlots] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [personnummer, setPersonnummer] = useState('');
  
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Load slots when step changes to 2
  useEffect(() => {
    if (step === 2) {
      const fetchSlots = async () => {
        setLoadingSlots(true);
        try {
          const res = await fetch(`/api/v1/schedule/optimal-slots?exam_type=${duration}&target_date=${targetDate}`);
          const data = await res.json();
          setSlots(data);
        } catch (err) {
          setError('Kunde inte läsa in lediga tider.');
        } finally {
          setLoadingSlots(false);
        }
      };
      fetchSlots();
    }
  }, [step, duration, targetDate]);

  const [bookingResult, setBookingResult] = useState(null);

  const handleBook = async () => {
    if (!personnummer) {
      setError('Vänligen ange personnummer.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        personal_number: personnummer,
        date: selectedSlot.date,
        time: selectedSlot.time,
        duration_type: duration,
        device_id: selectedSlot.device_id
      };
      const res = await fetch('/api/v1/webdoc/booking', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Bokning misslyckades.');
      }
      // Set custom duration if different from default
      const defaultDays = {'24h':1,'48h':2,'72h':3}[duration] || 1;
      if (customDays !== defaultDays && data.exam_id) {
        try {
          await fetch(`/api/v1/exams/${data.exam_id}/duration`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ duration_days: customDays })
          });
        } catch (e) { console.warn('Could not set custom duration', e); }
      }
      setBookingResult(data);
      setStep(4);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  const DURATION_INFO = {
    '24h': { label: 'Holter 24h', days: '1 dag', code: 'E1005' },
    '48h': { label: 'Holter 48h', days: '2 dagar', code: 'E1006' },
    '72h': { label: 'Holter 72h', days: '3+ dagar', code: 'E1007' },
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex justify-between items-center p-5 border-b border-slate-100 bg-slate-50">
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <Calendar className="text-indigo-500" size={20} />
            Intelligent Bokning
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors p-1 rounded-lg hover:bg-slate-100">
            <X size={18} />
          </button>
        </div>

        {/* Step indicator */}
        <div className="px-5 py-2 border-b border-slate-100 flex items-center gap-2">
          {[1, 2, 3, 4].map(s => (
            <div key={s} className="flex items-center gap-2">
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all ${
                step === s ? 'bg-indigo-600 text-white' 
                : step > s ? 'bg-emerald-100 text-emerald-700' 
                : 'bg-slate-100 text-slate-400'
              }`}>
                {step > s ? '✓' : s}
              </span>
              {s < 4 && <div className={`w-6 h-0.5 rounded ${step > s ? 'bg-emerald-200' : 'bg-slate-100'}`} />}
            </div>
          ))}
          <span className="ml-2 text-[10px] text-slate-400">
            {step === 1 ? 'Välj typ' : step === 2 ? 'Välj tid' : step === 3 ? 'Bekräfta' : 'Klar'}
          </span>
        </div>

        {error && (
          <div className="mx-5 mt-3 p-3 rounded-lg bg-red-50 border border-red-200 flex items-center gap-2 text-red-700 text-xs">
            <AlertTriangle size={14} />
            {error}
          </div>
        )}

        {/* Content */}
        <div className="p-5 flex-1 overflow-y-auto">
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">Välj undersökningstyp</h3>
              <div className="grid grid-cols-3 gap-3">
                {['24h', '48h', '72h'].map(t => (
                  <button
                    key={t}
                    onClick={() => { setDuration(t); setCustomDays({'24h':1,'48h':2,'72h':3}[t]); }}
                    className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${
                      duration === t 
                        ? 'bg-indigo-50 border-indigo-300 text-indigo-700 shadow-sm' 
                        : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
                    }`}
                  >
                    {t === '72h' ? <Package size={22} /> : <Clock size={22} />}
                    <span className="font-bold text-lg">{t}</span>
                    <span className="text-[10px] text-slate-400">{DURATION_INFO[t].days}</span>
                  </button>
                ))}
              </div>

              {/* Custom measurement days */}
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <div className="text-[10px] text-slate-400 uppercase tracking-widest font-medium mb-2">Mätdagar (override)</div>
                <div className="flex items-center gap-1.5">
                  {[1, 2, 3, 4, 5, 6, 7].map(d => (
                    <button
                      key={d}
                      onClick={() => setCustomDays(d)}
                      className={`flex-1 py-2 rounded-lg text-xs font-semibold transition-all
                        ${customDays === d 
                          ? 'bg-indigo-600 text-white shadow-sm' 
                          : 'bg-white text-slate-500 border border-slate-200 hover:border-indigo-200 hover:text-indigo-600'}`}
                    >
                      {d}d
                    </button>
                  ))}
                </div>
                <p className="text-[10px] text-slate-400 mt-2">
                  Standard för {DURATION_INFO[duration].label}: {DURATION_INFO[duration].days} · Valt: <strong>{customDays} dagar</strong>
                </p>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setStep(2)}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2 rounded-lg text-sm font-semibold shadow-sm transition-colors flex items-center gap-2"
                >
                  Visa lediga tider <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}


          {step === 2 && (
            <div className="space-y-4">
              <div className="flex justify-between items-center mb-2">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Lediga Tider</h3>
                <span className="text-[10px] text-indigo-500 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded-full font-medium">
                  {DURATION_INFO[duration].label}
                </span>
              </div>
              
              {loadingSlots ? (
                <div className="py-8 text-center text-slate-400 animate-pulse text-sm">Beräknar tillgängliga tider...</div>
              ) : slots.length === 0 ? (
                <div className="py-8 text-center">
                  <AlertTriangle size={24} className="mx-auto text-amber-400 mb-2" />
                  <p className="text-sm text-slate-600">Inga lediga tider hittades.</p>
                  <p className="text-xs text-slate-400 mt-1">Testa en annan undersökningstyp eller vecka.</p>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {slots.map((slot, i) => (
                    <button
                      key={i}
                      onClick={() => setSelectedSlot(slot)}
                      className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all text-left ${
                        selectedSlot === slot
                          ? 'bg-indigo-50 border-indigo-300 ring-1 ring-indigo-200'
                          : 'bg-white border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`text-sm font-bold ${selectedSlot === slot ? 'text-indigo-700' : 'text-slate-700'}`}>
                          {slot.is_now ? (
                            <span className="flex items-center gap-1.5">
                              <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                              </span>
                              Nu
                            </span>
                          ) : slot.time}
                        </div>
                        <div>
                          <div className="text-xs text-slate-600">
                            {slot.is_now ? `Idag ${slot.date} kl ${slot.time}` : slot.date}
                          </div>
                          <div className="text-[10px] text-slate-400">
                            {slot.device_code} · Retur: {slot.expected_return_at}
                          </div>
                        </div>
                      </div>
                      {selectedSlot === slot && (
                        <CheckCircle size={16} className="text-indigo-600" />
                      )}
                      {slot.is_now && selectedSlot !== slot && (
                        <span className="text-[9px] text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded font-semibold">DIREKT</span>
                      )}
                      {!slot.optimal_match && !slot.is_now && selectedSlot !== slot && (
                        <span className="text-[9px] text-amber-500 bg-amber-50 px-1.5 py-0.5 rounded">alt.</span>
                      )}
                    </button>
                  ))}
                </div>
              )}

              <div className="mt-5 flex justify-between">
                <button
                  onClick={() => setStep(1)}
                  className="text-slate-500 hover:text-slate-700 px-3 py-2 text-sm font-medium transition-colors flex items-center gap-1"
                >
                  <ArrowLeft size={14} /> Tillbaka
                </button>
                <button
                  disabled={!selectedSlot}
                  onClick={() => setStep(3)}
                  className="bg-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-indigo-700 text-white px-5 py-2 rounded-lg text-sm font-semibold shadow-sm transition-colors flex items-center gap-2"
                >
                  Välj tid <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-5">
              {/* Selected slot summary */}
              <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
                <div className="text-[10px] text-indigo-400 uppercase tracking-widest font-medium">Vald tid</div>
                <div className="text-lg font-bold text-indigo-800 mt-1">
                  {selectedSlot?.date} kl {selectedSlot?.time}
                </div>
                <div className="text-xs text-indigo-600 mt-1">
                  {DURATION_INFO[duration].label} · Enhet {selectedSlot?.device_code} · Förväntas tillbaka {selectedSlot?.expected_return_at}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-2">Patientens Personnummer</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="text-slate-400" size={16} />
                  </div>
                  <input
                    type="text"
                    value={personnummer}
                    onChange={(e) => setPersonnummer(e.target.value)}
                    placeholder="ÅÅÅÅMMDD-XXXX"
                    className="w-full bg-white border border-slate-200 rounded-lg pl-10 pr-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-300"
                  />
                </div>
                <p className="text-[10px] text-slate-400 mt-1.5">
                  Skapar automatiskt en Webdoc-bokning med åtgärdskod {DURATION_INFO[duration].code}.
                </p>
              </div>

              <div className="mt-4 flex justify-between">
                <button
                  onClick={() => setStep(2)}
                  className="text-slate-500 hover:text-slate-700 px-3 py-2 text-sm font-medium transition-colors flex items-center gap-1"
                >
                  <ArrowLeft size={14} /> Tillbaka
                </button>
                <button
                  onClick={handleBook}
                  disabled={submitting || !personnummer}
                  className="bg-emerald-600 flex items-center gap-2 hover:bg-emerald-700 text-white px-5 py-2 rounded-lg text-sm font-semibold shadow-sm transition-colors disabled:opacity-40"
                >
                  {submitting ? (
                    <span className="animate-pulse">Bokar i Webdoc...</span>
                  ) : (
                    <>
                      <CheckCircle size={16} /> Bekräfta Bokning
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-5 text-center py-4">
              <div className="w-16 h-16 rounded-full bg-emerald-50 flex items-center justify-center mx-auto">
                <CheckCircle size={32} className="text-emerald-500" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-800">Bokning skapad!</h3>
                <p className="text-sm text-slate-500 mt-1">
                  {selectedSlot?.date} kl {selectedSlot?.time} · {duration} · {selectedSlot?.device_code}
                </p>
              </div>
              
              {bookingResult && !bookingResult.webdoc_booking_id && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-left">
                  <div className="text-xs text-amber-800 font-medium flex items-center gap-1.5">
                    <AlertTriangle size={12} />
                    Webdoc-bokning kunde inte skapas automatiskt
                  </div>
                  <p className="text-[10px] text-amber-700 mt-1">
                    Bokningen finns i Pulsus. Skapa bokningen manuellt i Webdoc med åtgärdskod <strong>{DURATION_INFO[duration].code}</strong>.
                  </p>
                </div>
              )}

              {bookingResult?.webdoc_booking_id && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-left">
                  <div className="text-xs text-emerald-800 font-medium flex items-center gap-1.5">
                    <CheckCircle size={12} />
                    Webdoc-bokning skapad med ID: {bookingResult.webdoc_booking_id}
                  </div>
                </div>
              )}

              <button
                onClick={onBookingSuccess}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold shadow-sm transition-colors"
              >
                Stäng & uppdatera schema
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
