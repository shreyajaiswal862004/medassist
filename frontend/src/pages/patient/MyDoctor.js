import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';

export default function MyDoctor() {
    const { user, logout } = useAuth();
    const [doctor, setDoctor] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadDoctor();
    }, []);

    const loadDoctor = async () => {
        try {
            const response = await client.get('/api/patient/my-doctor');
            setDoctor(response.data);
        } catch (err) {
            console.log('No doctor assigned yet');
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
                    <p className="text-xs text-gray-500 mt-1">AI Medical Assistant</p>
                </div>
                <nav className="flex-1 p-4 space-y-1">
                    <a href="/patient/chat" className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm">
                        💬 Chat
                    </a>
                    <a href="/patient/reports" className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm">
                        📄 My Reports
                    </a>
                    <div className="flex items-center gap-3 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium">
                        🏥 My Doctor
                    </div>
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
            <div className="flex-1 p-8">
                <h2 className="text-2xl font-bold text-gray-800 mb-6">My Doctor</h2>

                {loading ? (
                    <div className="text-gray-400">Loading...</div>
                ) : !doctor ? (
                    <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
                        <p className="text-4xl mb-4">👨‍⚕️</p>
                        <p className="font-medium">No doctor assigned yet</p>
                        <p className="text-sm mt-1">Ask your admin to assign a doctor to your account</p>
                    </div>
                ) : (
                    <div className="bg-white rounded-xl border p-6 max-w-md">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center text-green-600 text-2xl font-bold">
                                {doctor.name?.[0]}
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-gray-800">{doctor.name}</h3>
                                <p className="text-gray-500 text-sm">{doctor.email}</p>
                                <span className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded-full mt-1 inline-block">
                                    Your assigned doctor
                                </span>
                            </div>
                        </div>
                        <div className="border-t pt-4">
                            <p className="text-sm text-gray-500">
                                Your doctor reviews all AI-generated responses before they are finalized.
                                For urgent concerns, please visit the nearest clinic or call emergency services.
                            </p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}