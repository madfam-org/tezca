"use client";

import { useState, useEffect } from 'react';
import { RefreshCW, Play, XCircle, CheckCircle2 } from 'lucide-react';

export default function IngestionPage() {
    const [status, setStatus] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState("all");

    const API_URL = "http://localhost:8000/api/v1"; // Should use env var

    const fetchStatus = async () => {
        try {
            const res = await fetch(`${API_URL}/ingest/`);
            const data = await res.json();
            setStatus(data);
        } catch (e) {
            console.error("Failed to fetch status", e);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 3000); // Poll every 3s
        return () => clearInterval(interval);
    }, []);

    const handleStart = async () => {
        setLoading(true);
        try {
            await fetch(`${API_URL}/ingest/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ mode: mode }),
            });
            // Immediate refresh
            fetchStatus();
        } catch (e) {
            alert("Failed to start ingestion");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="px-4 py-6 sm:px-0">
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Ingestion Control</h2>
                <p className="mt-1 text-sm text-gray-500">Manage synchronization with official sources.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Status Panel */}
                <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Current Status</h3>

                    {status ? (
                        <div className="space-y-4">
                            <div className="flex items-center space-x-2">
                                {status.status === 'running' && <RefreshCW className="w-5 h-5 text-blue-500 animate-spin" />}
                                {status.status === 'completed' && <CheckCircle2 className="w-5 h-5 text-green-500" />}
                                {status.status === 'failed' && <XCircle className="w-5 h-5 text-red-500" />}
                                {status.status === 'idle' && <div className="w-5 h-5 bg-gray-300 rounded-full" />}

                                <span className="text-xl font-semibold capitalize">{status.status}</span>
                            </div>

                            <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded-md font-mono text-sm">
                                {status.message}
                            </div>

                            <div className="text-xs text-gray-400">
                                Last updated: {status.timestamp}
                            </div>
                        </div>
                    ) : (
                        <div>Loading status...</div>
                    )}
                </div>

                {/* Controls Panel */}
                <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Actions</h3>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Ingestion Mode
                            </label>
                            <select
                                className="block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2"
                                value={mode}
                                onChange={(e) => setMode(e.target.value)}
                            >
                                <option value="all">Full Sync (All Laws)</option>
                                <option value="priority">Priority Laws Only</option>
                                <option value="daily">Daily Update</option>
                            </select>
                        </div>

                        <button
                            onClick={handleStart}
                            disabled={loading || status?.status === 'running'}
                            className={`w-full flex items-center justify-center space-x-2 py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white 
                 ${status?.status === 'running'
                                    ? 'bg-gray-400 cursor-not-allowed'
                                    : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                                }`}
                        >
                            <Play className="w-4 h-4" />
                            <span>{loading ? "Starting..." : "Start Ingestion"}</span>
                        </button>

                        {status?.status === 'running' && (
                            <p className="text-xs text-yellow-600 mt-2">
                                ⚠️ Ingestion is currently running. Please wait for it to finish.
                            </p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
