import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import client from '../api/client';

export default function Login() {
    const [isRegister, setIsRegister] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        role: 'patient'
    });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            if (isRegister) {
                // register first
                await client.post('/api/auth/register', formData);
            }

            // then login
            const response = await client.post('/api/auth/login', {
                email: formData.email,
                password: formData.password
            });

            const { access_token, role, user_id, name } = response.data;

            // save to auth context
            login({ role, user_id, name }, access_token);

            // redirect based on role
            if (role === 'patient') navigate('/patient/chat');
            else if (role === 'doctor') navigate('/doctor/overview');
            else if (role === 'admin') navigate('/admin/users');

        } catch (err) {
            setError(err.response?.data?.detail || 'Something went wrong');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <div className="bg-white p-8 rounded-xl shadow-md w-full max-w-md">

                {/* logo */}
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-blue-600">MedAssist</h1>
                    <p className="text-gray-500 mt-1">AI Medical Assistant</p>
                </div>

                {/* tabs */}
                <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
                    <button
                        className={`flex-1 py-2 rounded-md text-sm font-medium transition ${!isRegister ? 'bg-white shadow text-blue-600' : 'text-gray-500'}`}
                        onClick={() => setIsRegister(false)}
                    >
                        Login
                    </button>
                    <button
                        className={`flex-1 py-2 rounded-md text-sm font-medium transition ${isRegister ? 'bg-white shadow text-blue-600' : 'text-gray-500'}`}
                        onClick={() => setIsRegister(true)}
                    >
                        Register
                    </button>
                </div>

                {/* form */}
                <form onSubmit={handleSubmit} className="space-y-4">
                    {isRegister && (
                        <input
                            type="text"
                            placeholder="Full name"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className="w-full border rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            required
                        />
                    )}

                    <input
                        type="email"
                        placeholder="Email address"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className="w-full border rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                    />

                    <input
                        type="password"
                        placeholder="Password"
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        className="w-full border rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                    />

                    {isRegister && (
                        <select
                            value={formData.role}
                            onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                            className="w-full border rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="patient">Patient</option>
                            <option value="doctor">Doctor</option>
                            <option value="admin">Admin</option>
                        </select>
                    )}

                    {error && (
                        <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-50"
                    >
                        {loading ? 'Please wait...' : isRegister ? 'Create account' : 'Login'}
                    </button>
                </form>

                <p className="text-center text-xs text-gray-400 mt-6">
                    MedAssist is for informational support only.
                    Not a substitute for medical advice.
                </p>
            </div>
        </div>
    );
}