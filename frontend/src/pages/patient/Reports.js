import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';

export default function Reports() {
    const { user, logout } = useAuth();
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadReports();
    }, []);

    const loadReports = async () => {
        try {
            const response = await client.get('/api/patient/reports');
            setReports(response.data.reports || []);
        } catch (err) {
            console.log('No reports yet');
        } finally {
            setLoading(false);
        }
    };

    const getTypeIcon = (type) => {
        const icons = {
            'text': '💬',
            'prescription': '💊',
            'xray': '🩻',
            'ct_scan': '🧠',
            'pdf': '📄',
            'lab_values': '🔬',
            'voice': '🎤',
        };
        return icons[type] || '📋';
    };

    return (
        <div className="flex h-screen bg-gray-50">
            {/* sidebar */}
            <div className="w-64 bg-white border-r flex flex-col">
                <div className="p-4 border-b">
                    <h1 className="text-xl font-bold text-blue-600">MedAssist</h1>
                    <p className="text-xs text-gray-500 mt-1">AI Medical Assistant</p>
                </div>
                <nav className="flex-1 p-4 space-y-1">
                    <a href="/patient/chat" className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm">
                        💬 Chat
                    </a>
                    <div className="flex items-center gap-3 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium">
                        📄 My Reports
                    </div>
                    <a href="/patient/my-doctor" className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm">
                        🏥 My Doctor
                    </a>
                    <a href="/patient/history" className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm">
                        📋 History
                    </a>
                </nav>
                <div className="p-4 border-t">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-medium text-sm">
                            {user?.name?.[0]?.toUpperCase()}
                        </div>
                        <div>
                            <p className="text-sm font-medium text-gray-700">{user?.name}</p>
                            <p className="text-xs text-gray-400">Patient</p>
                        </div>
                    </div>
                    <button onClick={logout} className="text-sm text-gray-500 hover:text-red-500">Logout</button>
                </div>
            </div>

            {/* main content */}
            <div className="flex-1 p-8 overflow-y-auto">
                <h2 className="text-2xl font-bold text-gray-800 mb-6">My Reports</h2>

                {loading ? (
                    <div className="text-gray-400">Loading...</div>
                ) : reports.length === 0 ? (
                    <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
                        <p className="text-4xl mb-4">📂</p>
                        <p className="font-medium">No reports yet</p>
                        <p className="text-sm mt-1">Upload a prescription or medical report in the chat</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {reports.map((report, i) => (
                            <div key={i} className="bg-white rounded-xl border p-4 flex items-start gap-4">
                                <div className="text-3xl">{getTypeIcon(report.input_type)}</div>
                                <div className="flex-1">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="font-medium text-gray-700 capitalize">
                                            {report.input_type?.replace('_', ' ') || 'Report'}
                                        </span>
                                        <span className="text-xs text-gray-400">
                                            {new Date(report.timestamp).toLocaleDateString()}
                                        </span>
                                    </div>
                                    <p className="text-sm text-gray-500 line-clamp-2">{report.content}</p>
                                    <div className="flex items-center gap-2 mt-2">
                                        <span className={`text-xs px-2 py-0.5 rounded-full ${report.is_emergency
                                            ? 'bg-red-100 text-red-700'
                                            : 'bg-green-100 text-green-700'
                                            }`}>
                                            {report.is_emergency ? '🚨 Emergency' : '✅ Normal'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}