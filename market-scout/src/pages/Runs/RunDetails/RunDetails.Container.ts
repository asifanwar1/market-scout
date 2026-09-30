import { parseAsInteger, parseAsString, useQueryStates } from "nuqs";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { ACTIVE_RUN_STATUSES } from "@/constants/run-status.constants";
import { useCancelRun, useGetRun, useGetRunTasks, useResumeRun } from "@/hooks/api/runs.queries";
import { showToast } from "@/lib/toast";

const TASK_PAGE_SIZE = 20;

const urlState = {
    taskStatus: parseAsString,
    taskPage: parseAsInteger.withDefault(1),
};

export const useRunDetails = () => {
    const { id } = useParams();
    const runId = Number(id) || undefined;

    const { data: run, isPending, isError } = useGetRun(runId);
    const isActive = !!run && ACTIVE_RUN_STATUSES.includes(run.status);

    const [state, setState] = useQueryStates(urlState, { history: "replace" });
    const { data: tasks, isPending: isTasksLoading } = useGetRunTasks(
        runId,
        { page: state.taskPage, limit: TASK_PAGE_SIZE, status: state.taskStatus ?? undefined },
        isActive,
    );

    const { mutateAsync: cancelRun, isPending: isCancelling } = useCancelRun();
    const { mutateAsync: resumeRun, isPending: isResuming } = useResumeRun();
    const [showCancel, setShowCancel] = useState(false);

    // An interrupted run keeps its unfinished searches, so it can pick up where it stopped.
    const unfinished = run ? run.tasks_total - run.tasks_done - run.tasks_failed - run.tasks_skipped : 0;
    const canResume = run?.status === "failed" && unfinished > 0;

    const handleCancel = async () => {
        if (!runId) return;
        await cancelRun(runId);
        showToast.info("Cancelling: the run stops after its current search");
        setShowCancel(false);
    };

    const handleResume = async () => {
        if (!runId) return;
        await resumeRun(runId);
        showToast.success("Run resumed");
    };

    return {
        run,
        isLoading: isPending,
        isError,
        isActive,
        tasks: tasks?.data ?? [],
        tasksTotal: tasks?.count ?? 0,
        isTasksLoading,
        taskPage: state.taskPage,
        taskPageSize: TASK_PAGE_SIZE,
        taskStatus: state.taskStatus,
        setTaskStatus: (status: string | null) => void setState({ taskStatus: status, taskPage: 1 }),
        setTaskPage: (page: number) => void setState({ taskPage: page }),
        showCancel,
        setShowCancel,
        handleCancel,
        isCancelling,
        handleResume,
        isResuming,
        canResume,
    };
};
