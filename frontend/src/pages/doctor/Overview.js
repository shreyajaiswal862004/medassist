import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';
import { useNavigate } from 'react-router-dom';
import PatientDetailModal from '../../components/PatientDetailModal';

export default function DoctorOverview() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [patients, setPatients] = useState([]);
    const [reviewQueue, setReviewQueue] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedPatientId, setSelectedPatientId] = useState(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [patientsRes, reviewRes] = await Promise.all([
                client.get('/api/doctor/patients'),
                client.get('/api/doctor/review-queue')
            ]);
            setPatients(patientsRes.data.patients || []);
            setReviewQueue(reviewRes.data.pending_reviews || []);
        } catch (err) {
            console.log('Error loading data:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex h-screen bg-gray-50">

            {/* sidebar */}
            <div className="w-64 bg-white border-r flex flex-col">
                <div className="p-4 border-b">
                    <h1 className="text-xl font-bold text-blue-600">MedAssist</h1>
                    <p className="text-xs text-gray-500 mt-1">Doctor Portal</p>
                </div>

                <nav className="flex-1 p-4 space-y-1">
                    <div className="flex items-center gap-3 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium">
                        📊 Overview
                    </div>
                    <div
                        onClick={() => navigate('/doctor/review')}
                        className="flex items-center justify-between px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm cursor-pointer"
                    >
                        <span>⏳ Review Queue</span>
                        {reviewQueue.length > 0 && (
                            <span className="bg-amber-100 text-amber-700 text-xs px-2 py-0.5 rounded-full font-medium">
                                {reviewQueue.length}
                            </span>
                        )}
                    </div>
                    <div
                        onClick={() => navigate('/doctor/patients')}
                        className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm cursor-pointer"
                    >
                        👥 My Patients
                    </div>
                    <div
                        onClick={() => navigate('/doctor/appointments')}
                        className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm cursor-pointer"
                    >
                        📅 Appointments
                    </div>
                </nav>

                <div className="p-4 border-t">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center text-green-600 font-medium text-sm">
                            {user?.name?.[0]?.toUpperCase()}
                        </div>
                        <div>
                            <p className="text-sm font-medium text-gray-700">{user?.name}</p>
                            <p className="text-xs text-gray-400">Doctor</p>
                        </div>
                    </div>
                    <button onClick={logout} className="w-full text-sm text-gray-500 hover:text-red-500 text-left">
                        Logout
                    </button>
                </div>
            </div>

            {/* main content */}
            <div className="flex-1 overflow-y-auto">
                <div className="p-6">

                    {/* header */}
                    <div className="mb-6">
                        <h2 className="text-2xl font-bold text-gray-800">
                            Good morning, {user?.name}
                        </h2>
                        <p className="text-gray-500 text-sm mt-1">Here's your overview for today</p>
                    </div>

                    {/* stats */}
                    <div className="grid grid-cols-4 gap-4 mb-6">
                        <div
                            onClick={() => navigate('/doctor/patients')}
                            className="bg-white rounded-xl p-4 border cursor-pointer hover:border-blue-300 hover:shadow-sm transition"
                        >
                            <p className="text-sm text-gray-500">Total patients</p>
                            <p className="text-2xl font-bold text-gray-800 mt-1">{patients.length}</p>
                        </div>
                        <div
                            onClick={() => navigate('/doctor/review')}
                            className="bg-white rounded-xl p-4 border cursor-pointer hover:border-blue-300 hover:shadow-sm transition"
                        >
                            <p className="text-sm text-gray-500">Pending reviews</p>
                            <p className="text-2xl font-bold text-amber-500 mt-1">{reviewQueue.length}</p>
                        </div>
                        <div className="bg-white rounded-xl p-4 border">
                            <p className="text-sm text-gray-500">Reviewed today</p>
                            <p className="text-2xl font-bold text-green-500 mt-1">0</p>
                        </div>
                        <div className="bg-white rounded-xl p-4 border">
                            <p className="text-sm text-gray-500">Emergency alerts</p>
                            <p className="text-2xl font-bold text-red-500 mt-1">0</p>
                        </div>
                    </div>

                    {/* review queue */}
                    {reviewQueue.length > 0 && (
                        <div className="bg-white rounded-xl border mb-6">
                            <div className="p-4 border-b flex items-center justify-between">
                                <h3 className="font-semibold text-gray-700">Pending Reviews</h3>
                                <span className="bg-amber-100 text-amber-700 text-xs px-2 py-1 rounded-full">
                                    {reviewQueue.length} pending
                                </span>
                            </div>
                            {reviewQueue.map((review, i) => (
                                <div key={i} className="p-4 border-b last:border-0 flex items-center gap-4">
                                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-medium">
                                        {review.patient_name?.[0]}
                                    </div>
                                    <div className="flex-1">
                                        <p className="font-medium text-gray-700">{review.patient_name}</p>
                                        <p className="text-sm text-gray-500 truncate">{review.original_message}</p>
                                        <p className="text-xs text-amber-600 mt-1">
                                            Confidence: {(review.confidence * 100).toFixed(0)}% — needs review
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => navigate('/doctor/review')}
                                        className="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700"
                                    >
                                        Review
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* patients list */}
                    <div className="bg-white rounded-xl border">
                        <div className="p-4 border-b flex items-center justify-between">
                            <h3 className="font-semibold text-gray-700">My Patients</h3>
                            <button
                                onClick={() => navigate('/doctor/patients')}
                                className="text-xs font-semibold text-blue-600 hover:underline"
                            >
                                View All Patients →
                            </button>
                        </div>
                        {loading ? (
                            <div className="p-8 text-center text-gray-400">Loading...</div>
                        ) : patients.length === 0 ? (
                            <div className="p-8 text-center text-gray-400">
                                No patients assigned yet. Ask admin to assign patients.
                            </div>
                        ) : (
                            patients.map((patient, i) => (
                                <div
                                    key={i}
                                    onClick={() => setSelectedPatientId(patient.id)}
                                    className="p-4 border-b last:border-0 flex items-center gap-4 cursor-pointer hover:bg-blue-50/50 transition group"
                                >
                                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-medium group-hover:bg-blue-600 group-hover:text-white transition">
                                        {patient.name?.[0]}
                                    </div>
                                    <div className="flex-1">
                                        <p className="font-medium text-gray-700 group-hover:text-blue-600 transition">{patient.name}</p>
                                        <p className="text-sm text-gray-500">{patient.email}</p>
                                    </div>
                                    <span className="bg-green-100 text-green-700 text-xs px-2.5 py-1 rounded-full font-medium">
                                        Active
                                    </span>
                                    <span className="text-xs text-blue-600 font-medium opacity-0 group-hover:opacity-100 transition">
                                        View Details →
                                    </span>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* Patient Detail Modal */}
            {selectedPatientId && (
                <PatientDetailModal
                    patientId={selectedPatientId}
                    onClose={() => setSelectedPatientId(null)}
                    onScheduleAppointment={(patient) => navigate('/doctor/appointments', { state: { patientName: patient.name } })}
                />
            )}
        </div>
    );
}