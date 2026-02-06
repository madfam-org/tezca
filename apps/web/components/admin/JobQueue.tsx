'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { IngestionStatus } from '@leyesmx/lib';
import { PlayCircle, CheckCircle, AlertCircle, Clock } from 'lucide-react';

export function JobQueue() {
    const [jobs, setJobs] = useState<IngestionStatus[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchJobs = async () => {
        try {
            const data = await api.listJobs();
            setJobs(data.jobs || []);
        } catch (err) {
            console.error('Failed to fetch jobs:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchJobs();
        const interval = setInterval(fetchJobs, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    if (loading && jobs.length === 0) {
        return <div className="animate-pulse h-24 bg-muted rounded-lg" />;
    }

    if (jobs.length === 0) {
        return (
            <div className="border rounded-lg p-8 text-center bg-card">
                <p className="text-muted-foreground">No active or recent jobs found.</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {jobs.map((job, index) => (
                <div key={job.timestamp || index} className="border rounded-lg p-4 bg-card flex items-center justify-between">
                    <div className="flex items-start gap-3">
                        {job.status === 'running' && <PlayCircle className="text-blue-500 mt-1" />}
                        {job.status === 'completed' && <CheckCircle className="text-green-500 mt-1" />}
                        {job.status === 'error' && <AlertCircle className="text-red-500 mt-1" />}
                        {job.status === 'idle' && <Clock className="text-muted-foreground mt-1" />}
                        
                        <div>
                            <h3 className="font-medium capitalize">{job.status} Job</h3>
                            {job.message && <p className="text-sm text-muted-foreground">{job.message}</p>}
                            {job.timestamp && (
                                <p className="text-xs text-muted-foreground mt-1">
                                    Last update: {new Date(job.timestamp).toLocaleString()}
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
