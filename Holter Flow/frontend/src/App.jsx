import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ScheduleView from './pages/ScheduleView';
import DeviceManager from './pages/DeviceManager';
import PostalManager from './pages/PostalManager';
import ActiveDevices from './pages/ActiveDevices';
import Guide from './pages/Guide';
import LoginPage from './pages/LoginPage';

function App() {
  const [authed, setAuthed] = useState(() => sessionStorage.getItem('pulsus_auth') === 'true');

  if (!authed) {
    return <LoginPage onLogin={() => setAuthed(true)} />;
  }

  return (
    <Router>
      <Layout onLogout={() => { sessionStorage.clear(); setAuthed(false); }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/schedule" element={<ScheduleView />} />
          <Route path="/devices" element={<DeviceManager />} />
          <Route path="/postal" element={<PostalManager />} />
          <Route path="/active" element={<ActiveDevices />} />
          <Route path="/guide" element={<Guide />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
