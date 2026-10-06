import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function Appointments() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    // sample appointments — in production these come from database
    const [appointments, setAppointments] = useState([
        {
            id: 1,
            patient_name: "Riya Shah",
            patient_initial: "R",
            date: "2026-10-22",
            time: "11:00 AM",
            type: "Follow-up",
            notes: "Blood sugar review",
            status: "scheduled"
        },
        {
            id: 2,
            patient_name: "Meera Joshi",
            patient_initial: "M",
            date: "2026-10-22",
            time: "2:30 PM",
            type: "New patient",
            notes: "First consultation",
            status: "scheduled"
        },
        {
            id: 3,
            patient_name: "Riya Shah",
            patient_initial: "R",
            date: "2026-10-23",
            time: "10:00 AM",
            type: "Report review",
            notes: "CBC and HbA1c review",
            status: "scheduled"
        }
    ]);

    const [showForm, setShowForm] = useState(false);
    const [newAppt, setNewAppt] = useState({
        patient_name: '',
        date: '',
        time: '',
        type: 'Follow-up',
        notes: ''
    });

    const addAppointment = () => {
        if (!newAppt.patient_name || !newAppt.date || !newAppt.time) return;
        setAppointments(prev => [...prev, {
            id: prev.length + 1,
            ...newAppt,
            patient_initial: newAppt.patient_name[0].toUpperCase(),
            status: 'scheduled'
        }]);
        setShowForm(false);
        setNewAppt({ patient_name: '', date: '', time: '', type: 'Follow-up', notes: '' });
    };

    const cancelAppointment = (id) => {
        setAppointments(prev => prev.map(a =>
            a.id === id ? { ...a, status: 'cancelled' } : a
        ));
    };

    const today = new Date().toISOString().split('T')[0];
    const todayAppts = appointments.filter(a => a.date === today && a.status === 'scheduled');
    const upcomingAppts = appointments.filter(a => a.date > today && a.status === 'scheduled');

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
                        className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm cursor-pointer"
                    >
                        ⏳ Review Queue
                    </div>
                    <div
                        onClick={() => navigate('/doctor/patients')}
                        className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm cursor-pointer"
                    >
                        👥 My Patients
                    </div>
                    <div className="flex items-center gap-3 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium">
                        📅 Appointments
                    </div>
                </nav>
                <div className="p-4 border-t">
                    <p className="text-sm font-medium text-gray-700">{user?.name}</p>
                    <p className="text-xs text-gray-400 mb-2">Doctor</p>
                    <button onClick={logout} className="text-sm text-gray-500 hover:text-red-500">
                        Logout
                    </button>
                </div>
            </div>

            {/* main content */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold text-gray-800">Appointments</h2>
                    <button
                        onClick={() => setShowForm(!showForm)}
                        className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
                    >
                        + Add appointment
                    </button>
                </div>

                {/* add appointment form */}
                {showForm && (
                    <div className="bg-white rounded-xl border p-4 mb-6">
                        <h3 className="font-semibold text-gray-700 mb-4">New appointment</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <input
                                type="text"
                                placeholder="Patient name"
                                value={newAppt.patient_name}
                                onChange={(e) => setNewAppt({ ...newAppt, patient_name: e.target.value })}
                                className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                            <select
                                value={newAppt.type}
                                onChange={(e) => setNewAppt({ ...newAppt, type: e.target.value })}
                                className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option>Follow-up</option>
                                <option>New patient</option>
                                <option>Report review</option>
                                <option>Emergency</option>
                            </select>
                            <input
                                type="date"
                                value={newAppt.date}
                                onChange={(e) => setNewAppt({ ...newAppt, date: e.target.value })}
                                className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                            <input
                                type="time"
                                value={newAppt.time}
                                onChange={(e) => setNewAppt({ ...newAppt, time: e.target.value })}
                                className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                            <input
                                type="text"
                                placeholder="Notes (optional)"
                                value={newAppt.notes}
                                onChange={(e) => setNewAppt({ ...newAppt, notes: e.target.value })}
                                className="border rounded-lg px-3 py-2 text-sm col-span-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <div className="flex gap-3 mt-4">
                            <button
                                onClick={addAppointment}
                                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
                            >
                                Save
                            </button>
                            <button
                                onClick={() => setShowForm(false)}
                                className="border px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                )}

                {/* today */}
                <div className="bg-white rounded-xl border mb-6">
                    <div className="p-4 border-b flex items-center justify-between">
                        <h3 className="font-semibold text-gray-700">Today</h3>
                        <span className="text-sm text-gray-400">{new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}</span>
                    </div>
                    {todayAppts.length === 0 ? (
                        <div className="p-6 text-center text-gray-400 text-sm">No appointments today</div>
                    ) : (
                        todayAppts.map((appt, i) => (
                            <div key={i} className="p-4 border-b last:border-0 flex items-center gap-4">
                                <div className="text-center min-w-16">
                                    <p className="text-lg font-bold text-gray-800">{appt.time.split(':')[0]}</p>
                                    <p className="text-xs text-gray-400">{appt.time.includes('AM') ? 'AM' : 'PM'}</p>
                                </div>
                                <div className="w-1 h-12 bg-blue-200 rounded flex-shrink-0"></div>
                                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-medium flex-shrink-0">
                                    {appt.patient_initial}
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-gray-700">{appt.patient_name}</p>
                                    <p className="text-sm text-gray-500">{appt.type} — {appt.notes}</p>
                                </div>
                                <span className="bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded-full">
                                    {appt.time}
                                </span>
                                <button
                                    onClick={() => cancelAppointment(appt.id)}
                                    className="text-red-400 text-xs hover:text-red-600"
                                >
                                    Cancel
                                </button>
                            </div>
                        ))
                    )}
                </div>

                {/* upcoming */}
                <div className="bg-white rounded-xl border">
                    <div className="p-4 border-b">
                        <h3 className="font-semibold text-gray-700">Upcoming</h3>
                    </div>
                    {upcomingAppts.length === 0 ? (
                        <div className="p-6 text-center text-gray-400 text-sm">No upcoming appointments</div>
                    ) : (
                        upcomingAppts.map((appt, i) => (
                            <div key={i} className="p-4 border-b last:border-0 flex items-center gap-4">
                                <div className="text-center min-w-16">
                                    <p className="text-sm font-bold text-gray-800">
                                        {new Date(appt.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                                    </p>
                                    <p className="text-xs text-gray-400">{appt.time}</p>
                                </div>
                                <div className="w-1 h-12 bg-gray-200 rounded flex-shrink-0"></div>
                                <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center text-gray-600 font-medium flex-shrink-0">
                                    {appt.patient_initial}
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-gray-700">{appt.patient_name}</p>
                                    <p className="text-sm text-gray-500">{appt.type} — {appt.notes}</p>
                                </div>
                                <span className="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded-full">
                                    Upcoming
                                </span>
                                <button
                                    onClick={() => cancelAppointment(appt.id)}
                                    className="text-red-400 text-xs hover:text-red-600"
                                >
                                    Cancel
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}