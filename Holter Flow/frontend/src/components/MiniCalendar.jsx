import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const DAYS_SV = ['Mån', 'Tis', 'Ons', 'Tor', 'Fre', 'Lör', 'Sön'];
const MONTHS_SV = ['Januari', 'Februari', 'Mars', 'April', 'Maj', 'Juni', 'Juli', 'Augusti', 'September', 'Oktober', 'November', 'December'];

function getDaysInMonth(year, month) {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfWeek(year, month) {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1; // Monday=0
}

export default function MiniCalendar({ selectedDate, onSelect, minDate }) {
  const initial = selectedDate ? new Date(selectedDate) : new Date();
  const [viewYear, setViewYear] = useState(initial.getFullYear());
  const [viewMonth, setViewMonth] = useState(initial.getMonth());

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const minD = minDate ? new Date(minDate) : today;
  minD.setHours(0, 0, 0, 0);

  const daysInMonth = getDaysInMonth(viewYear, viewMonth);
  const firstDay = getFirstDayOfWeek(viewYear, viewMonth);

  const prevMonth = () => {
    if (viewMonth === 0) { setViewYear(viewYear - 1); setViewMonth(11); }
    else setViewMonth(viewMonth - 1);
  };
  const nextMonth = () => {
    if (viewMonth === 11) { setViewYear(viewYear + 1); setViewMonth(0); }
    else setViewMonth(viewMonth + 1);
  };

  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const formatDate = (y, m, d) => `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-sm w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <button onClick={prevMonth} className="p-1 rounded hover:bg-slate-100 text-slate-500 transition-colors">
          <ChevronLeft size={14} />
        </button>
        <span className="text-xs font-semibold text-slate-700">
          {MONTHS_SV[viewMonth]} {viewYear}
        </span>
        <button onClick={nextMonth} className="p-1 rounded hover:bg-slate-100 text-slate-500 transition-colors">
          <ChevronRight size={14} />
        </button>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 gap-0.5 mb-1">
        {DAYS_SV.map(d => (
          <div key={d} className="text-[9px] text-slate-400 text-center font-medium py-0.5">{d}</div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7 gap-0.5">
        {cells.map((day, i) => {
          if (day === null) return <div key={`empty-${i}`} />;

          const dateStr = formatDate(viewYear, viewMonth, day);
          const cellDate = new Date(viewYear, viewMonth, day);
          cellDate.setHours(0, 0, 0, 0);
          const isDisabled = cellDate < minD;
          const isSelected = dateStr === selectedDate;
          const isToday = cellDate.getTime() === today.getTime();

          return (
            <button
              key={day}
              disabled={isDisabled}
              onClick={() => onSelect(dateStr)}
              className={`text-[10px] py-1.5 rounded-lg font-medium transition-all
                ${isSelected
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : isToday
                    ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                    : isDisabled
                      ? 'text-slate-200 cursor-not-allowed'
                      : 'text-slate-600 hover:bg-slate-100'
                }`}
            >
              {day}
            </button>
          );
        })}
      </div>
    </div>
  );
}
