import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';

export default function PatientChat() {
    const { user, logout } = useAuth();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [uploadedFile, setUploadedFile] = useState(null);
    const messagesEndRef = useRef(null);
    const fileInputRef = useRef(null);

    // scroll to bottom when new message arrives
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // load chat history on page load
    useEffect(() => {
        loadHistory();
    }, []);

    const loadHistory = async () => {
        try {
            const response = await client.get('/api/patient/history');
            const history = response.data.messages || [];
            setMessages(history.map(msg => ({
                role: msg.role,
                content: msg.content,
                isEmergency: msg.is_emergency,
                timestamp: msg.timestamp
            })));
        } catch (err) {
            console.log('No history yet');
        }
    };

    const sendMessage = async () => {
        if (!input.trim() && !uploadedFile) return;
        setLoading(true);

        // add user message to UI immediately
        const userMessage = {
            role: 'user',
            content: input || `Uploaded: ${uploadedFile?.name}`,
            timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, userMessage]);
        const currentInput = input;
        setInput('');

        try {
            let response;

            if (uploadedFile) {
                // file upload
                const formData = new FormData();
                formData.append('file', uploadedFile);
                if (currentInput) formData.append('message', currentInput);
                response = await client.post('/api/upload', formData);
                setUploadedFile(null);
            } else {
                // text message
                response = await client.post(`/api/chat?message=${encodeURIComponent(currentInput)}`);
            }

            const data = response.data;

            // add AI response to UI
            const aiMessage = {
                role: 'assistant',
                content: formatResponse(data),
                isEmergency: data.is_emergency,
                emergencyAlert: data.emergency_alert,
                disclaimer: data.disclaimer,
                timestamp: new Date().toISOString()
            };
            setMessages(prev => [...prev, aiMessage]);

        } catch (err) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Sorry, something went wrong. Please try again.',
                isEmergency: false,
                timestamp: new Date().toISOString()
            }]);
        } finally {
            setLoading(false);
        }
    };

    const formatResponse = (data) => {
        if (data.possible_conditions) {
            return [
                `Possible conditions: ${data.possible_conditions.join(', ')}`,
                `\nReasoning: ${data.reasoning}`,
                `\nNext steps: ${data.recommended_next_steps?.join(', ')}`
            ].join('');
        }
        return JSON.stringify(data, null, 2);
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
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
                    <div className="flex items-center gap-3 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium">
                        💬 Chat
                    </div>
                    <a href="/patient/reports" className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm">
                        📄 My Reports
                    </a>
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
                    <button
                        onClick={logout}
                        className="w-full text-sm text-gray-500 hover:text-red-500 text-left"
                    >
                        Logout
                    </button>
                </div>
            </div>

            {/* main chat area */}
            <div className="flex-1 flex flex-col">

                {/* top bar */}
                <div className="bg-white border-b px-6 py-4">
                    <h2 className="font-semibold text-gray-700">Chat with MedAssist</h2>
                    <p className="text-xs text-gray-400">Describe your symptoms or upload a report</p>
                </div>

                {/* messages */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">

                    {messages.length === 0 && (
                        <div className="text-center text-gray-400 mt-20">
                            <p className="text-4xl mb-4">🏥</p>
                            <p className="text-lg font-medium">Hello, {user?.name}</p>
                            <p className="text-sm mt-1">Describe your symptoms or upload a medical report</p>
                        </div>
                    )}

                    {messages.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-2xl ${msg.role === 'user' ? 'order-2' : 'order-1'}`}>

                                {/* emergency alert */}
                                {msg.emergencyAlert && (
                                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-2 text-red-700 text-sm font-medium">
                                        🚨 {msg.emergencyAlert}
                                    </div>
                                )}

                                {/* message bubble */}
                                <div className={`rounded-2xl px-4 py-3 text-sm ${msg.role === 'user'
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-white border text-gray-700'
                                    }`}>
                                    <p className="whitespace-pre-wrap">{msg.content}</p>
                                </div>

                                {/* disclaimer */}
                                {msg.disclaimer && (
                                    <p className="text-xs text-gray-400 mt-1 px-1">{msg.disclaimer}</p>
                                )}

                            </div>
                        </div>
                    ))}

                    {/* loading indicator */}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="bg-white border rounded-2xl px-4 py-3 text-sm text-gray-500">
                                Analyzing...
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* uploaded file preview */}
                {uploadedFile && (
                    <div className="px-6 py-2 bg-blue-50 border-t flex items-center gap-2">
                        <span className="text-sm text-blue-600">📎 {uploadedFile.name}</span>
                        <button
                            onClick={() => setUploadedFile(null)}
                            className="text-red-400 text-xs hover:text-red-600"
                        >
                            remove
                        </button>
                    </div>
                )}

                {/* input area */}
                <div className="bg-white border-t p-4">
                    <div className="flex gap-3 items-end">
                        {/* file upload button */}
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="p-3 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition"
                            title="Upload file"
                        >
                            📎
                        </button>
                        <input
                            ref={fileInputRef}
                            type="file"
                            className="hidden"
                            accept=".jpg,.jpeg,.png,.pdf,.mp3,.wav"
                            onChange={(e) => setUploadedFile(e.target.files[0])}
                        />

                        {/* text input */}
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Describe your symptoms..."
                            className="flex-1 border rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                            rows={2}
                        />

                        {/* send button */}
                        <button
                            onClick={sendMessage}
                            disabled={loading || (!input.trim() && !uploadedFile)}
                            className="bg-blue-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-blue-700 transition disabled:opacity-50"
                        >
                            Send
                        </button>
                    </div>

                    <p className="text-xs text-gray-400 mt-2 text-center">
                        MedAssist is for informational support only — not a substitute for a licensed doctor
                    </p>
                </div>
            </div>
        </div>
    );
}