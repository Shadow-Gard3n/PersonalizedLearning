
import { Navigate, Route, Routes } from "react-router-dom";

import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import LearningSession from "./pages/LearningSession";


function ProtectedRoute({ children }) {
  const token = localStorage.getItem("access_token");

  return token ? children : <Navigate to="/login" replace />;
}


export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/session/:sessionId"
        element={
          <ProtectedRoute>
            <LearningSession />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}