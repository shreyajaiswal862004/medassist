import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import MyDoctor from './pages/patient/MyDoctor';
import Reports from './pages/patient/Reports';
import History from './pages/patient/History';


// pages — we will create these next
import Login from './pages/Login';
import PatientChat from './pages/patient/Chat';
import DoctorOverview from './pages/doctor/Overview';
import DoctorReviewQueue from './pages/doctor/ReviewQueue';
import DoctorPatients from './pages/doctor/Patients';
import Appointments from './pages/doctor/Appointments';
import AdminUsers from './pages/admin/Users';

// protected route — redirects to login if not logged in
function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();

  if (loading) return <div className="flex items-center justify-center h-screen">Loading...</div>;

  if (!user) return <Navigate to="/login" />;

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/login" />;
  }

  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Navigate to="/login" />} />

          {/* patient routes */}
          <Route path="/patient/chat" element={
            <ProtectedRoute allowedRoles={['patient']}>
              <PatientChat />
            </ProtectedRoute>
          } />

          <Route path="/patient/my-doctor" element={
            <ProtectedRoute allowedRoles={['patient']}>
              <MyDoctor />
            </ProtectedRoute>
          } />

          <Route path="/patient/reports" element={
            <ProtectedRoute allowedRoles={['patient']}>
              <Reports />
            </ProtectedRoute>
          } />

          <Route path="/patient/history" element={
            <ProtectedRoute allowedRoles={['patient']}>
              <History />
            </ProtectedRoute>
          } />

          {/* doctor routes */}
          <Route path="/doctor/overview" element={
            <ProtectedRoute allowedRoles={['doctor']}>
              <DoctorOverview />
            </ProtectedRoute>
          } />
          <Route path="/doctor/review" element={
            <ProtectedRoute allowedRoles={['doctor']}>
              <DoctorReviewQueue />
            </ProtectedRoute>
          } />

          <Route path="/doctor/patients" element={
            <ProtectedRoute allowedRoles={['doctor']}>
              <DoctorPatients />
            </ProtectedRoute>
          } />

          <Route path="/doctor/appointments" element={
            <ProtectedRoute allowedRoles={['doctor']}>
              <Appointments />
            </ProtectedRoute>
          } />

          {/* admin routes */}
          <Route path="/admin/users" element={
            <ProtectedRoute allowedRoles={['admin']}>
              <AdminUsers />
            </ProtectedRoute>
          } />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;