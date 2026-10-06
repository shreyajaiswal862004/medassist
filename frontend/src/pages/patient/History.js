import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';

export default function History() {
    const { user, logout } = useAuth();
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadHistory();
    }, []);

    const loadHistory = async () => {
        try {
            const response = await client.get('/api/patient/history');
            setMessages(response.data.messages || []);
        } catch (err) {
            console.log('No history yet');
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
                    <a href="/patient/my-doctor" className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm">
                        🏥 My Doctor
                    </a>
                    <div className="flex items-center gap-3 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium">
                        📋 History
                    </div>
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
                <h2 className="text-2xl font-bold text-gray-800 mb-6">Chat History</h2>

                {loading ? (
                    <div className="text-gray-400">Loading...</div>
                ) : messages.length === 0 ? (
                    <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
                        <p className="text-4xl mb-4">📋</p>
                        <p className="font-medium">No history yet</p>
                        <p className="text-sm mt-1">Start a chat to see your history here</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {messages.map((msg, i) => (
                            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-2xl rounded-2xl px-4 py-3 text-sm ${msg.role === 'user'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-white border text-gray-700'
                                    }`}>
                                    {msg.is_emergency && (
                                        <div className="bg-red-100 text-red-700 text-xs px-2 py-1 rounded mb-2">
                                            🚨 Emergency flagged
                                        </div>
                                    )}
                                    <p className="whitespace-pre-wrap">{msg.content}</p>
                                    <p className={`text-xs mt-1 ${msg.role === 'user' ? 'text-blue-200' : 'text-gray-400'}`}>
                                        {new Date(msg.timestamp).toLocaleString()}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}