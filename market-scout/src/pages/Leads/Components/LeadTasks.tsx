import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import type { TTask } from "@/api/services/pipeline/pipeline.response.types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { TASK_TITLE_MAX_LENGTH } from "@/constants/limits.constants";
import { DRAWER_LIST_LIMIT, TASK_SCOPE } from "@/constants/pipeline.constants";
import { useCreateTask, useDeleteTask, useGetTasks, useUpdateTask } from "@/hooks/api/pipeline.queries";
import { cn } from "@/lib/utils";
import { showToast } from "@/lib/toast";
import { DUE_TONE, defaultDueStamp, describeDue, todayStamp, type DueTone } from "@/utils/pipeline.utils";

const EMPTY_TEXT = "No follow-ups. Add one so this lead doesn't go cold.";
const TITLE_PLACEHOLDER = "e.g. Call back about the quote";

const TONE_CLASSES: Record<DueTone, string> = {
    [DUE_TONE.OVERDUE]: "text-destructive",
    [DUE_TONE.TODAY]: "text-warning-foreground",
    [DUE_TONE.UPCOMING]: "text-muted-foreground",
};

type TLeadTasksProps = {
    businessId: number;
};

const LeadTasks = ({ businessId }: TLeadTasksProps) => {
    const today = todayStamp();
    const { data } = useGetTasks({ scope: TASK_SCOPE.OPEN, business_id: businessId, today, limit: DRAWER_LIST_LIMIT });
    const { mutateAsync: createTask, isPending: isCreating } = useCreateTask();
    const { mutateAsync: updateTask } = useUpdateTask();
    const { mutateAsync: deleteTask } = useDeleteTask();

    const [title, setTitle] = useState("");
    const [dueOn, setDueOn] = useState(defaultDueStamp);

    const tasks = data?.data ?? [];
    const canAdd = title.trim().length > 0 && dueOn !== "" && !isCreating;

    const submit = async () => {
        await createTask({ id: businessId, body: { title: title.trim(), due_on: dueOn } });
        setTitle("");
        setDueOn(defaultDueStamp());
        showToast.success("Follow-up added");
    };

    const complete = async (task: TTask) => {
        await updateTask({ id: task.id, body: { done: true } });
        showToast.success("Marked done");
    };

    const remove = async (task: TTask) => {
        await deleteTask(task.id);
    };

    const renderTask = (task: TTask) => {
        const due = describeDue(task.due_on, today);
        return (
            <li key={task.id} className="flex items-start gap-3">
                <Checkbox className="mt-0.5" aria-label={`Mark "${task.title}" done`} onCheckedChange={() => complete(task)} />
                <div className="min-w-0 flex-1">
                    <p className="break-words text-sm font-medium">{task.title}</p>
                    <p className={cn("text-xs", TONE_CLASSES[due.tone])}>
                        {due.label}
                        {task.assigned_to && <span className="text-muted-foreground"> · {task.assigned_to.full_name}</span>}
                    </p>
                </div>
                <Button variant="ghost" size="icon-xs" aria-label={`Delete "${task.title}"`} onClick={() => remove(task)}>
                    <Trash2 />
                </Button>
            </li>
        );
    };

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
                <Input
                    className="min-w-40 flex-1"
                    maxLength={TASK_TITLE_MAX_LENGTH}
                    value={title}
                    placeholder={TITLE_PLACEHOLDER}
                    aria-label="Follow-up"
                    onChange={(event) => setTitle(event.target.value)}
                />
                <Input
                    type="date"
                    className="w-40"
                    value={dueOn}
                    aria-label="Due date"
                    onChange={(event) => setDueOn(event.target.value)}
                />
                <Button size="sm" className="self-center" disabled={!canAdd} onClick={submit}>
                    <Plus />
                    Add
                </Button>
            </div>

            {tasks.length === 0 ? (
                <p className="text-sm text-muted-foreground">{EMPTY_TEXT}</p>
            ) : (
                <ul className="space-y-3">{tasks.map(renderTask)}</ul>
            )}
        </div>
    );
};

export default LeadTasks;
