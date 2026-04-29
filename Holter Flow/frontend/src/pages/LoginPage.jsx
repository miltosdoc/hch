import { useState } from 'react';
import { Lock, User, AlertTriangle, Eye, EyeOff } from 'lucide-react';
import newLogo from '../assets/new_logo.png';

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Simulate a brief auth delay for UX
    await new Promise(r => setTimeout(r, 600));

    if (username === 'admin' && password === '123456') {
      sessionStorage.setItem('pulsus_auth', 'true');
      sessionStorage.setItem('pulsus_user', username);
      onLogin();
    } else {
      setError('Fel användarnamn eller lösenord');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 relative overflow-hidden">
      <div className="relative z-10 w-full max-w-md px-4">
        {/* Login Card */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-[0_20px_25px_-5px_rgba(0,0,0,0.05)] overflow-hidden">
          
          {/* Header */}
          <div className="bg-[#323e4f] pt-10 pb-6 px-8 flex flex-col items-center text-center border-b border-slate-800">
            <img src={newLogo} alt="Pulsus Logo" className="h-16 mb-4" />
            <h1 className="text-xl font-extrabold text-white tracking-widest uppercase mb-1" 
                style={{ fontFamily: "'Montserrat', sans-serif" }}>
              Pulsus Tracker
            </h1>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-8 space-y-5">
            {error && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-red-500 text-xs font-medium">
                <AlertTriangle size={14} />
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div className="relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                  <User size={16} />
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="Användarnamn"
                  autoComplete="username"
                  autoFocus
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl pl-11 pr-4 py-3.5 text-sm
                             text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#5b8a9b] 
                             focus:ring-2 focus:ring-[#5b8a9b]/20 transition-all"
                />
              </div>

              <div className="relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                  <Lock size={16} />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Lösenord"
                  autoComplete="current-password"
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl pl-11 pr-12 py-3.5 text-sm
                             text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#5b8a9b] 
                             focus:ring-2 focus:ring-[#5b8a9b]/20 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full bg-[#323e4f] hover:bg-[#2b3643] 
                         text-white font-semibold py-3.5 rounded-xl shadow-md shadow-[#323e4f]/20
                         transition-all duration-200 hover:shadow-lg hover:scale-[1.01]
                         disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100
                         flex items-center justify-center gap-2 text-sm"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Loggar in…
                </>
              ) : (
                'Logga in'
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="px-8 pb-6 text-center">
            <p className="text-[11px] text-slate-400">
              © 2026 Hjärtcentrum Halland · Pulsus Tracker
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
