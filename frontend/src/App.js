import { useEffect, useState } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Chat from "./pages/Chat";
import JoinChat from "./pages/JoinChat";

// BACKEND URL
export const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8001';
export const API = `${API_BASE}/api`;

// THIS IS WHERE OUR WEBSITE IS HOSTED
export const MY_HOMEPAGE_URL = API_BASE?.match(/-([a-z0-9]+)\./)?.[1]
  ? `https://${API_BASE?.match(/-([a-z0-9]+)\./)?.[1]}.previewer.live`
  : window.location.origin;

console.log(`API: ${API}`);
console.log(`MY_HOMEPAGE_URL: ${MY_HOMEPAGE_URL}`);

// Auth utilities
export const getAuthToken = () => localStorage.getItem("authToken");
export const getUser = () => {
  const userStr = localStorage.getItem("user");
  return userStr ? JSON.parse(userStr) : null;
};
export const setAuth = (token, user) => {
  localStorage.setItem("authToken", token);
  localStorage.setItem("user", JSON.stringify(user));
};
export const clearAuth = () => {
  localStorage.removeItem("authToken");
  localStorage.removeItem("user");
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const token = getAuthToken();
  return token ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/invite/:token" element={<JoinChat />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/chat/:chatId"
            element={
              <ProtectedRoute>
                <Chat />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
