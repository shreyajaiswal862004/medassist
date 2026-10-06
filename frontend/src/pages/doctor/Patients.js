import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';
import { useNavigate } from 'react-router-dom';
import PatientDetailModal from '../../components/PatientDetailModal';

export default function DoctorPatients() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [patients, setPatients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedPatientId, setSelectedPatientId] = useState(null);

    useEffect(() => {
        loadPatients();
    }, []);

    const loadPatients = async () => {
        try {
            const res = await client.get('/api/doctor/patients');
            setPatients(res.data.patients || []);
        } catch (err) {
            console.error('Error loading patients:', err);
        } finally {
            setLoading(false);
        }
    };

    const filteredPatients = patients.filter(p =>
        p.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.email?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleScheduleAppointment = (patient) => {
        navigate('/doctor/appointments', { state: { patientName: patient.name } });
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
                    <div
                        onClick={() => navigate('/doctor/overview')}
                        className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm cursor-pointer"
                    >
                        📊 Overview
                    </div>
                    <div
                        onClick={() => navigate('/doctor/review')}
                        className="flex items-center justify-between px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm cursor-pointer"
                    >
                        <span>⏳ Review Queue</span>
                    </div>
                    <div
                        className="flex items-center gap-3 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium cursor-pointer"
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
            <div className="flex-1 overflow-y-auto p-6">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-800">My Patients</h2>
                        <p className="text-sm text-gray-500 mt-1">Manage and view medical records of assigned patients</p>
                    </div>
                    <input
                        type="text"
                        placeholder="Search patient by name or email..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-72 border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white shadow-sm"
                    />
                </div>

                {loading ? (
                    <div className="p-12 text-center text-gray-400">Loading assigned patients...</div>
                ) : filteredPatients.length === 0 ? (
                    <div className="bg-white rounded-xl border p-12 text-center text-gray-400">
                        {searchQuery ? 'No patients found matching your search.' : 'No patients assigned to you yet.'}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredPatients.map((patient) => (
                            <div
                                key={patient.id}
                                onClick={() => setSelectedPatientId(patient.id)}
                                className="bg-white rounded-xl border p-5 shadow-sm hover:shadow-md transition cursor-pointer flex flex-col justify-between group border-gray-200 hover:border-blue-300"
                            >
                                <div>
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="w-12 h-12 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center font-bold text-lg group-hover:bg-blue-600 group-hover:text-white transition">
                                            {patient.name?.[0]?.toUpperCase()}
                                        </div>
                                        <span className="bg-green-100 text-green-700 text-xs px-2.5 py-1 rounded-full font-medium">
                                            Active
                                        </span>
                                    </div>
                                    <h3 className="font-semibold text-gray-800 text-lg group-hover:text-blue-600 transition">
                                        {patient.name}
                                    </h3>
                                    <p className="text-sm text-gray-500 mt-0.5">{patient.email}</p>
                                </div>

                                <div className="mt-6 pt-4 border-t flex items-center justify-between text-xs text-gray-400">
                                    <span>Patient ID: #{patient.id}</span>
                                    <span className="text-blue-600 font-medium group-hover:underline">View Medical History →</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Modal */}
            {selectedPatientId && (
                <PatientDetailModal
                    patientId={selectedPatientId}
                    onClose={() => setSelectedPatientId(null)}
                    onScheduleAppointment={handleScheduleAppointment}
                />
            )}
        </div>
    );
}
