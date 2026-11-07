import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import "./index.css";
import Commitments from "./pages/Commitments";
import ContactProfile from "./pages/ContactProfile";
import Contacts from "./pages/Contacts";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import MeetingDetail from "./pages/MeetingDetail";
import Meetings from "./pages/Meetings";
import MemoryIntelligence from "./pages/MemoryIntelligence";
import Prepare from "./pages/Prepare";
import SettingsPage from "./pages/Settings";

function Protected() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner />;
  return user ? <Layout /> : <Navigate to="/login" replace />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Protected />}>
            <Route index element={<Dashboard />} />
            <Route path="meetings" element={<Meetings />} />
            <Route path="meetings/:id" element={<MeetingDetail />} />
            <Route path="meetings/:id/prepare" element={<Prepare />} />
            <Route path="contacts" element={<Contacts />} />
            <Route path="contacts/:id" element={<ContactProfile />} />
            <Route path="commitments" element={<Commitments />} />
            <Route path="memory" element={<MemoryIntelligence />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
