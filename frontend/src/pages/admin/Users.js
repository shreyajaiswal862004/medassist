import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';

export default function AdminUsers() {
    const { user, logout } = useAuth();
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [assignData, setAssignData] = useState({ patient_id: '', doctor_id: '' });
    const [message, setMessage] = useState('');

    useEffect(() => {
        loadUsers();
    }, []);

    const loadUsers = async () => {
        try {
            const response = await client.get('/api/admin/users');
            setUsers(response.data.users || []);
        } catch (err) {
            console.log('Error:', err);
        } finally {
            setLoading(false);
        }
    };

    const assignDoctor = async () => {
        try {
            await client.post('/api/admin/assign-doctor', null, {
                params: assignData
            });
            setMessage('Doctor assigned successfully');
            setTimeout(() => setMessage(''), 3000);
        } catch (err) {
            setMessage('Error assigning doctor');
        }
    };

    const patients = users.filter(u => u.role === 'patient');
    const doctors = users.filter(u => u.role === 'doctor');

    return (
        <div className="flex h-screen bg-gray-50">

            {/* sidebar */}
            <div className="w-64 bg-white border-r flex flex-col">
                <div className="p-4 border-b">
                    <h1 className="text-xl font-bold text-blue-600">MedAssist</h1>
                    <p className="text-xs text-gray-500 mt-1">Admin Portal</p>
                </div>
                <nav className="flex-1 p-4 space-y-1">
                    <div className="flex items-center gap-3 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium">
                        👥 All Users
                    </div>
                    <div className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm cursor-pointer">
                        🔗 Assign Doctor
                    </div>
                    <div className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm cursor-pointer">
                        📊 System Stats
                    </div>
                    <div className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm cursor-pointer">
                        📋 Audit Logs
                    </div>
                </nav>
                <div className="p-4 border-t">
                    <p className="text-sm font-medium text-gray-700">{user?.name}</p>
                    <p className="text-xs text-gray-400 mb-2">Admin</p>
                    <button onClick={logout} className="text-sm text-gray-500 hover:text-red-500">
                        Logout
                    </button>
                </div>
            </div>

            {/* main content */}
            <div className="flex-1 overflow-y-auto p-6">

                {/* stats */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="bg-white rounded-xl p-4 border">
                        <p className="text-sm text-gray-500">Total users</p>
                        <p className="text-2xl font-bold text-gray-800 mt-1">{users.length}</p>
                    </div>
                    <div className="bg-white rounded-xl p-4 border">
                        <p className="text-sm text-gray-500">Doctors</p>
                        <p className="text-2xl font-bold text-green-500 mt-1">{doctors.length}</p>
                    </div>
                    <div className="bg-white rounded-xl p-4 border">
                        <p className="text-sm text-gray-500">Patients</p>
                        <p className="text-2xl font-bold text-blue-500 mt-1">{patients.length}</p>
                    </div>
                </div>

                {/* assign doctor */}
                <div className="bg-white rounded-xl border p-4 mb-6">
                    <h3 className="font-semibold text-gray-700 mb-4">Assign Doctor to Patient</h3>
                    <div className="flex gap-3">
                        <select
                            value={assignData.patient_id}
                            onChange={(e) => setAssignData({ ...assignData, patient_id: e.target.value })}
                            className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">Select patient</option>
                            {patients.map(p => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                        </select>
                        <select
                            value={assignData.doctor_id}
                            onChange={(e) => setAssignData({ ...assignData, doctor_id: e.target.value })}
                            className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">Select doctor</option>
                            {doctors.map(d => (
                                <option key={d.id} value={d.id}>{d.name}</option>
                            ))}
                        </select>
                        <button
                            onClick={assignDoctor}
                            className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm hover:bg-blue-700"
                        >
                            Assign
                        </button>
                    </div>
                    {message && (
                        <p className="text-green-600 text-sm mt-2">{message}</p>
                    )}
                </div>

                {/* users table */}
                <div className="bg-white rounded-xl border">
                    <div className="p-4 border-b">
                        <h3 className="font-semibold text-gray-700">All Users</h3>
                    </div>
                    {loading ? (
                        <div className="p-8 text-center text-gray-400">Loading...</div>
                    ) : (
                        <table className="w-full">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="text-left p-4 text-xs font-medium text-gray-500">Name</th>
                                    <th className="text-left p-4 text-xs font-medium text-gray-500">Email</th>
                                    <th className="text-left p-4 text-xs font-medium text-gray-500">Role</th>
                                    <th className="text-left p-4 text-xs font-medium text-gray-500">Joined</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map((u, i) => (
                                    <tr key={i} className="border-t hover:bg-gray-50">
                                        <td className="p-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 text-sm font-medium">
                                                    {u.name?.[0]}
                                                </div>
                                                <span className="text-sm font-medium text-gray-700">{u.name}</span>
                                            </div>
                                        </td>
                                        <td className="p-4 text-sm text-gray-500">{u.email}</td>
                                        <td className="p-4">
                                            <span className={`text-xs px-2 py-1 rounded-full font-medium ${u.role === 'doctor' ? 'bg-green-100 text-green-700' :
                                                    u.role === 'admin' ? 'bg-purple-100 text-purple-700' :
                                                        'bg-blue-100 text-blue-700'
                                                }`}>
                                                {u.role}
                                            </span>
                                        </td>
                                        <td className="p-4 text-sm text-gray-500">
                                            {new Date(u.joined).toLocaleDateString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </div>
    );
}