export type TJobQueue = {
    kind: string;
    queued: number;
    running: number;
};

export type TFailedJob = {
    id: number;
    kind: string;
    ref_id: number;
    attempts: number;
    error: string | null;
    finished_at: string | null;
};

export type TJobsStatus = {
    workers_enabled: boolean;
    workers_running: boolean;
    queues: TJobQueue[];
    oldest_waiting_seconds: number | null;
    recent_failures: TFailedJob[];
};
