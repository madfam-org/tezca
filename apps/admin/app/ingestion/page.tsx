"use client";

import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input"; // Just for types/styles reference if needed, but we use native select here
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
        <div className="px-4 py-6 sm:px-0 space-y-6">
            <div className="mb-6">
                <h2 className="text-3xl font-bold tracking-tight">Ingestion Control</h2>
                <p className="text-muted-foreground">Manage synchronization with official sources.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Status Panel */}
                <Card>
                    <CardHeader>
                        <CardTitle>Current Status</CardTitle>
                        <CardDescription>Real-time status of the ingestion engine.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {status ? (
                            <div className="space-y-4">
                                <div className="flex items-center space-x-2">
                                    {status.status === 'running' && <RefreshCW className="w-5 h-5 text-blue-500 animate-spin" />}
                                    {status.status === 'completed' && <CheckCircle2 className="w-5 h-5 text-green-500" />}
                                    {status.status === 'failed' && <XCircle className="w-5 h-5 text-red-500" />}
                                    {status.status === 'idle' && <div className="w-5 h-5 bg-gray-300 rounded-full" />}

                                    <span className="text-xl font-semibold capitalize">{status.status}</span>
                                </div>

                                <div className="bg-muted p-4 rounded-md font-mono text-sm break-all">
                                    {status.message}
                                </div>

                                <div className="text-xs text-muted-foreground">
                                    Last updated: {status.timestamp}
                                </div>
                            </div>
                        ) : (
                            <div className="flex items-center space-x-2 text-muted-foreground">
                                <RefreshCW className="w-4 h-4 animate-spin" />
                                <span>Loading status...</span>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Controls Panel */}
                <Card>
                    <CardHeader>
                        <CardTitle>Actions</CardTitle>
                        <CardDescription>Trigger new ingestion tasks.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                                Ingestion Mode
                            </label>
                            <select
                                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                value={mode}
                                onChange={(e) => setMode(e.target.value)}
                            >
                                <option value="all">Full Sync (All Laws)</option>
                                <option value="priority">Priority Laws Only</option>
                                <option value="daily">Daily Update</option>
                            </select>
                        </div>

                        <Button
                            onClick={handleStart}
                            disabled={loading || status?.status === 'running'}
                            className="w-full"
                        >
                            {loading ? (
                                <RefreshCW className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <Play className="mr-2 h-4 w-4" />
                            )}
                            {loading ? "Starting..." : "Start Ingestion"}
                        </Button>

                        {status?.status === 'running' && (
                            <p className="text-xs text-yellow-600 dark:text-yellow-500 mt-2 flex items-center">
                                ⚠️ Ingestion is currently running. Please wait for it to finish.
                            </p>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
