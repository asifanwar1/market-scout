import { ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

import type { TTask } from "@/api/services/pipeline/pipeline.response.types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatDate, formatRelative } from "@/utils/format.utils";
import { DUE_TONE, describeDue, type DueTone } from "@/utils/pipeline.utils";
import { OPEN_LEAD_LABEL } from "../Tasks.constants";

const TONE_CLASSES: Record<DueTone, string> = {
    [DUE_TONE.OVERDUE]: "text-destructive",
    [DUE_TONE.TODAY]: "text-warning-foreground",
    [DUE_TONE.UPCOMING]: "text-muted-foreground",
};

const LEAD_ID_PARAM = "lead";

type TTaskRowProps = {
    task: TTask;
    today: string;
    isBusy: boolean;
    onToggle: (task: TTask) => void;
};

const TaskRow = ({ task, today, isBusy, onToggle }: TTaskRowProps) => {
    const isDone = task.completed_at !== null;
    const due = describeDue(task.due_on, today);
    const leadLink = `${APP_ROUTES.LEADS}?${LEAD_ID_PARAM}=${task.business_id}`;

    return (
        <li className="flex items-start gap-3 px-4 py-3">
            <Checkbox
                className="mt-1"
                checked={isDone}
                disabled={isBusy}
                aria-label={isDone ? `Reopen "${task.title}"` : `Mark "${task.title}" done`}
                onCheckedChange={() => onToggle(task)}
            />
            <div className="min-w-0 flex-1 space-y-0.5">
                <p className={cn("break-words text-sm font-medium", isDone && "text-muted-foreground line-through")}>{task.title}</p>
                <p className="text-xs text-muted-foreground">
                    {task.business_name}
                    {task.assigned_to && ` · ${task.assigned_to.full_name}`}
                </p>
                {isDone ? (
                    <p className="text-xs text-muted-foreground">Done {formatRelative(task.completed_at)}</p>
                ) : (
                    <p className={cn("text-xs", TONE_CLASSES[due.tone])}>
                        {due.label} · {formatDate(task.due_on)}
                    </p>
                )}
            </div>
            <Button asChild variant="ghost" size="icon-xs" aria-label={`${OPEN_LEAD_LABEL}: ${task.business_name}`}>
                <Link to={leadLink}>
                    <ExternalLink />
                </Link>
            </Button>
        </li>
    );
};

export default TaskRow;
