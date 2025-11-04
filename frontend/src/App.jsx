// src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom';
import { Home } from './pages/home';
import { Chat } from './pages/chat';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/chat" element={<Chat />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
