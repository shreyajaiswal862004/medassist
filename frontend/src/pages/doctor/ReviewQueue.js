import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';

export default function DoctorReviewQueue() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [reviews, setReviews] = useState([]);
    const [selected, setSelected] = useState(null);
    const [editedResponse, setEditedResponse] = useState('');
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        loadReviews();
    }, []);

    const loadReviews = async () => {
        try {
            const response = await client.get('/api/doctor/review-queue');
            setReviews(response.data.pending_reviews || []);
        } catch (err) {
            console.log('Error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleDecision = async (reviewId, decision) => {
        setSubmitting(true);
        try {
            await client.post(`/api/doctor/review/${reviewId}/decision`, null, {
                params: {
                    decision,
                    edited_response: decision === 'edit' ? editedResponse : null
                }
            });
            // remove from list
            setReviews(prev => prev.filter(r => r.review_id !== reviewId));
            setSelected(null);
        } catch (err) {
            console.log('Error:', err);
        } finally {
            setSubmitting(false);
        }
    };

    const selectReview = (review) => {
        setSelected(review);
        try {
            // ai_output is stored as a Python dict string, parse it
            const cleaned = review.ai_output
                .replace(/'/g, '"')
                .replace(/None/g, 'null')
                .replace(/True/g, 'true')
                .replace(/False/g, 'false');
            const parsed = JSON.parse(cleaned);
            const conditions = parsed.possible_conditions?.join(', ') || '';
            const reasoning = parsed.reasoning || '';
            const steps = parsed.recommended_next_steps?.join('. ') || '';
            setEditedResponse(
                `Possible conditions: ${conditions}\n\nReasoning: ${reasoning}\n\nNext steps: ${steps}`
            );
        } catch {
            setEditedResponse(review.ai_output);
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
                    <div
                        onClick={() => navigate('/doctor/overview')}
                        className="flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg text-sm cursor-pointer"
                    >
                        📊 Overview
                    </div>
                    <div className="flex items-center justify-between px-3 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium">
                        <span>⏳ Review Queue</span>
                        {reviews.length > 0 && (
                            <span className="bg-amber-100 text-amber-700 text-xs px-2 py-0.5 rounded-full">
                                {reviews.length}
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
                    <p className="text-sm font-medium text-gray-700">Dr. {user?.name}</p>
                    <button onClick={logout} className="text-sm text-gray-500 hover:text-red-500 mt-1">
                        Logout
                    </button>
                </div>
            </div>

            {/* review list */}
            <div className="w-80 bg-white border-r overflow-y-auto">
                <div className="p-4 border-b">
                    <h2 className="font-semibold text-gray-700">Review Queue</h2>
                    <p className="text-xs text-gray-400 mt-1">{reviews.length} pending</p>
                </div>
                {loading ? (
                    <div className="p-8 text-center text-gray-400">Loading...</div>
                ) : reviews.length === 0 ? (
                    <div className="p-8 text-center text-gray-400">
                        No pending reviews 🎉
                    </div>
                ) : (
                    reviews.map((review, i) => (
                        <div
                            key={i}
                            onClick={() => selectReview(review)}
                            className={`p-4 border-b cursor-pointer hover:bg-gray-50 ${selected?.review_id === review.review_id ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
                                }`}
                        >
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 bg-amber-100 rounded-full flex items-center justify-center text-amber-600 text-sm font-medium">
                                    {review.patient_name?.[0]}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-medium text-gray-700 text-sm">{review.patient_name}</p>
                                    <p className="text-xs text-gray-500 truncate">{review.original_message}</p>
                                </div>
                            </div>
                            <div className="mt-2 flex items-center gap-2">
                                <span className="bg-amber-100 text-amber-700 text-xs px-2 py-0.5 rounded-full">
                                    {(review.confidence * 100).toFixed(0)}% confidence
                                </span>
                                <span className="text-xs text-gray-400">pending</span>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* review detail */}
            <div className="flex-1 overflow-y-auto">
                {!selected ? (
                    <div className="flex items-center justify-center h-full text-gray-400">
                        <div className="text-center">
                            <p className="text-4xl mb-4">👈</p>
                            <p>Select a review from the queue</p>
                        </div>
                    </div>
                ) : (
                    <div className="p-6">
                        <div className="mb-6">
                            <h2 className="text-xl font-bold text-gray-800">
                                Review — {selected.patient_name}
                            </h2>
                            <span className="bg-amber-100 text-amber-700 text-sm px-3 py-1 rounded-full">
                                Confidence {(selected.confidence * 100).toFixed(0)}% — needs review
                            </span>
                        </div>

                        {/* patient message */}
                        <div className="bg-white rounded-xl border p-4 mb-4">
                            <h3 className="text-sm font-semibold text-gray-500 mb-2">PATIENT MESSAGE</h3>
                            <p className="text-gray-700">{selected.original_message}</p>
                        </div>

                        {/* AI response */}
                        <div className="bg-white rounded-xl border p-4 mb-4">
                            <h3 className="text-sm font-semibold text-gray-500 mb-2">AI SUGGESTED RESPONSE</h3>
                            <p className="text-gray-700 text-sm whitespace-pre-wrap">
                                {(() => {
                                    try {
                                        const cleaned = selected.ai_output
                                            .replace(/'/g, '"')
                                            .replace(/None/g, 'null')
                                            .replace(/True/g, 'true')
                                            .replace(/False/g, 'false');
                                        const parsed = JSON.parse(cleaned);
                                        return `Conditions: ${parsed.possible_conditions?.join(', ')}\n\nReasoning: ${parsed.reasoning}\n\nNext steps: ${parsed.recommended_next_steps?.join('. ')}`;
                                    } catch {
                                        return selected.ai_output;
                                    }
                                })()}
                            </p>
                        </div>

                        {/* editable response */}
                        <div className="bg-white rounded-xl border p-4 mb-6">
                            <h3 className="text-sm font-semibold text-gray-500 mb-2">
                                YOUR RESPONSE (edit before approving)
                            </h3>
                            <textarea
                                value={editedResponse}
                                onChange={(e) => setEditedResponse(e.target.value)}
                                className="w-full border rounded-lg p-3 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                                rows={6}
                            />
                        </div>

                        {/* action buttons */}
                        <div className="flex gap-3">
                            <button
                                onClick={() => handleDecision(selected.review_id, 'approve')}
                                disabled={submitting}
                                className="flex-1 bg-green-500 text-white py-3 rounded-xl font-medium hover:bg-green-600 transition disabled:opacity-50"
                            >
                                ✅ Approve and send
                            </button>
                            <button
                                onClick={() => handleDecision(selected.review_id, 'edit')}
                                disabled={submitting}
                                className="flex-1 bg-blue-500 text-white py-3 rounded-xl font-medium hover:bg-blue-600 transition disabled:opacity-50"
                            >
                                ✏️ Send edited version
                            </button>
                            <button
                                onClick={() => handleDecision(selected.review_id, 'reject')}
                                disabled={submitting}
                                className="flex-1 bg-red-500 text-white py-3 rounded-xl font-medium hover:bg-red-600 transition disabled:opacity-50"
                            >
                                ❌ Reject
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}