import React, { useState, useEffect, useCallback } from 'react';
import client from '../api/client';

export default function PatientDetailModal({ patientId, onClose, onScheduleAppointment }) {
    const [details, setDetails] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('history'); // 'history' | 'reports'

    const fetchPatientDetails = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await client.get(`/api/doctor/patient/${patientId}`);
            setDetails(res.data);
        } catch (err) {
            console.error('Error fetching patient details:', err);
            setError(err.response?.data?.detail || 'Failed to load patient records.');
        } finally {
            setLoading(false);
        }
    }, [patientId]);

    useEffect(() => {
        if (!patientId) return;
        fetchPatientDetails();
    }, [patientId, fetchPatientDetails]);

    if (!patientId) return null;

    const reports = details?.history?.filter(h => h.input_type && h.input_type !== 'text') || [];

    return (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-fadeIn">

                {/* Header */}
                <div className="p-5 border-b bg-gradient-to-r font-sans from-blue-600 to-indigo-600 text-white flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-white bg-opacity-20 text-white font-bold text-xl rounded-full flex items-center justify-center border border-white/30">
                            {details?.name?.[0]?.toUpperCase() || '?'}
                        </div>
                        <div>
                            <h2 className="text-xl font-bold">{details?.name || 'Loading...'}</h2>
                            <p className="text-xs text-blue-100">{details?.email || ''}</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="w-8 h-8 rounded-full bg-white bg-opacity-20 hover:bg-opacity-30 text-white flex items-center justify-center transition"
                    >
                        ✕
                    </button>
                </div>

                {/* Content Area */}
                {loading ? (
                    <div className="p-12 text-center text-gray-500">
                        <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mb-3"></div>
                        <p>Loading patient records...</p>
                    </div>
                ) : error ? (
                    <div className="p-8 text-center text-red-500">
                        <p className="font-semibold">{error}</p>
                        <button
                            onClick={fetchPatientDetails}
                            className="mt-4 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
                        >
                            Retry
                        </button>
                    </div>
                ) : (
                    <>
                        {/* Tabs */}
                        <div className="flex border-b bg-gray-50 px-5 gap-4">
                            <button
                                onClick={() => setActiveTab('history')}
                                className={`py-3 text-sm font-medium border-b-2 transition ${activeTab === 'history'
                                    ? 'border-blue-600 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                💬 Consultation History ({details.history?.length || 0})
                            </button>
                            <button
                                onClick={() => setActiveTab('reports')}
                                className={`py-3 text-sm font-medium border-b-2 transition ${activeTab === 'reports'
                                    ? 'border-blue-600 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                📄 Reports & Uploads ({reports.length})
                            </button>
                        </div>

                        {/* Body */}
                        <div className="flex-1 overflow-y-auto p-6 space-y-4">
                            {activeTab === 'history' && (
                                details.history?.length === 0 ? (
                                    <div className="text-center py-8 text-gray-400">
                                        No chat or consultation history recorded for this patient.
                                    </div>
                                ) : (
                                    details.history.map((msg) => (
                                        <div
                                            key={msg.id}
                                            className={`p-4 rounded-xl border ${msg.is_emergency
                                                ? 'border-red-300 bg-red-50'
                                                : msg.role === 'user'
                                                    ? 'border-blue-100 bg-blue-50/50'
                                                    : 'border-gray-200 bg-white'
                                                }`}
                                        >
                                            <div className="flex items-center justify-between mb-2">
                                                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${msg.role === 'user' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                                                    }`}>
                                                    {msg.role === 'user' ? 'Patient Input' : 'AI / Doctor Assistant'}
                                                </span>
                                                <span className="text-xs text-gray-400">
                                                    {new Date(msg.timestamp).toLocaleString()}
                                                </span>
                                            </div>
                                            <p className="text-sm text-gray-800 whitespace-pre-wrap">{msg.content}</p>
                                            {msg.is_emergency && (
                                                <span className="inline-block mt-2 text-xs font-bold text-red-600 bg-red-100 px-2 py-0.5 rounded">
                                                    🚨 Emergency Alert Flagged
                                                </span>
                                            )}
                                        </div>
                                    ))
                                )
                            )}

                            {activeTab === 'reports' && (
                                reports.length === 0 ? (
                                    <div className="text-center py-8 text-gray-400">
                                        No uploaded medical reports or scans found.
                                    </div>
                                ) : (
                                    reports.map((report) => (
                                        <div key={report.id} className="p-4 rounded-xl border border-gray-200 bg-white flex items-center justify-between">
                                            <div>
                                                <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                                                    {report.input_type}
                                                </span>
                                                <p className="text-sm text-gray-700 mt-1 font-medium">{report.content}</p>
                                                <p className="text-xs text-gray-400 mt-1">{new Date(report.timestamp).toLocaleString()}</p>
                                            </div>
                                        </div>
                                    ))
                                )
                            )}
                        </div>

                        {/* Footer actions */}
                        <div className="p-4 border-t bg-gray-50 flex justify-between items-center">
                            <span className="text-xs text-gray-400">Patient ID: #{details.id}</span>
                            <div className="flex gap-3">
                                {onScheduleAppointment && (
                                    <button
                                        onClick={() => {
                                            onClose();
                                            onScheduleAppointment(details);
                                        }}
                                        className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
                                    >
                                        📅 Schedule Appointment
                                    </button>
                                )}
                                <button
                                    onClick={onClose}
                                    className="px-4 py-2 bg-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-300 transition"
                                >
                                    Close
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
