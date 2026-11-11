// src/App.jsx
import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import LearningSession from './pages/LearningSession';

function App() {
  return (
    <div className="min-h-screen bg-gray-100 text-gray-900 font-sans">
      {/* Navbar */}
      <nav className="bg-white shadow-sm p-4 flex justify-between items-center mb-6">
        <h1 className="text-xl font-bold text-blue-700">AI Tutor Pro</h1>
        <div>
          <button 
            onClick={() => {
              localStorage.removeItem('token');
              window.location.href = '/login';
            }} 
            className="text-sm text-gray-600 hover:text-red-600"
          >
            Logout
          </button>
        </div>
      </nav>

      {/* Routes Only (No <Router> wrapper here) */}
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/session/:id" element={<LearningSession />} />
      </Routes>
    </div>
  );
}

export default App;