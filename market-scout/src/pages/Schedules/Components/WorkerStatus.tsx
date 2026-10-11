import { AlertTriangle, CheckCircle2 } from "lucide-react";

import type { TJobsStatus } from "@/api/services/jobs/jobs.response.types";
import { JOB_KIND_LABELS } from "@/constants/schedule.constants";
import { pluralize } from "@/utils/format.utils";
import { WORKER_DOWN_MESSAGE, WORKER_OFF_MESSAGE, WORKER_OK_LABEL } from "../Schedules.constants";

type TWorkerStatusProps = {
    status: TJobsStatus | undefined;
};

const WorkerStatus = ({ status }: TWorkerStatusProps) => {
    if (!status) return null;

    if (!status.workers_enabled || !status.workers_running) {
        const message = status.workers_enabled ? WORKER_DOWN_MESSAGE : WORKER_OFF_MESSAGE;
        return (
            <div role="alert" className="flex items-start gap-2 rounded-md bg-warning p-3 text-sm text-warning-foreground">
                <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                <p>{message}</p>
            </div>
        );
    }

    const waiting = status.queues.reduce((total, queue) => total + queue.queued, 0);
    const working = status.queues.filter((queue) => queue.running > 0).map((queue) => JOB_KIND_LABELS[queue.kind] ?? queue.kind);

    return (
        <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
            <CheckCircle2 className="size-3.5 text-success-foreground" />
            <span>{WORKER_OK_LABEL}</span>
            {waiting > 0 && <span>· {pluralize(waiting, "job waiting", "jobs waiting")}</span>}
            {working.length > 0 && <span>· working on {working.join(", ").toLowerCase()}</span>}
        </p>
    );
};

export default WorkerStatus;
