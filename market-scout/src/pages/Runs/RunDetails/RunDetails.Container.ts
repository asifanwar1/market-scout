import { parseAsInteger, parseAsString, useQueryStates } from "nuqs";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { FIRST_PAGE } from "@/constants";
import { ACTIVE_RUN_STATUSES, RUN_STATUS, getRunStatus } from "@/constants/run-status.constants";
import { useCancelRun, useGetRun, useGetRunTasks, useResumeRun } from "@/hooks/api/runs.queries";
import { showToast } from "@/lib/toast";
import { formatCount, formatDateTime, formatUsd, getSourceLabel } from "@/utils/format.utils";
import { NO_VALUE } from "./RunDetails.constants";

const TASK_PAGE_SIZE = 20;

const urlState = {
    taskStatus: parseAsString,
    taskPage: parseAsInteger.withDefault(FIRST_PAGE),
};

export const useRunDetails = () => {
    const { id } = useParams();
    const runId = Number(id) || undefined;

    const { data: run, isPending: isLoading, isError } = useGetRun(runId);
    const isActive = !!run && ACTIVE_RUN_STATUSES.includes(run.status);

    const [state, setState] = useQueryStates(urlState, { history: "replace" });
    const { data: tasksData, isPending: isTasksLoading } = useGetRunTasks(
        runId,
        { page: state.taskPage, limit: TASK_PAGE_SIZE, status: state.taskStatus ?? undefined },
        isActive,
    );

    const taskPage = state.taskPage;
    const tasks = tasksData?.data ?? [];
    const tasksTotal = tasksData?.count ?? 0;
    const taskPageSize = TASK_PAGE_SIZE;
    const taskStatus = state.taskStatus;

    const setTaskStatus = (nextStatus: string | null) => {
        void setState({ taskStatus: nextStatus, taskPage: FIRST_PAGE });
    };

    const setTaskPage = (page: number) => {
        void setState({ taskPage: page });
    };

    const { mutateAsync: cancelRun, isPending: isCancelling } = useCancelRun();
    const { mutateAsync: resumeRun, isPending: isResuming } = useResumeRun();
    const [showCancel, setShowCancel] = useState(false);

    const unfinished = run ? run.tasks_total - run.tasks_done - run.tasks_failed - run.tasks_skipped : 0;
    const canResume = run?.status === RUN_STATUS.FAILED && unfinished > 0;

    const openCancel = () => {
        setShowCancel(true);
    };

    const closeCancel = () => {
        setShowCancel(false);
    };

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

    const status = run ? getRunStatus(run.status) : undefined;
    const statusLabel = status?.label ?? run?.status ?? "";
    const statusClassName = status?.className;
    const finishedSearches = run ? run.tasks_done + run.tasks_failed + run.tasks_skipped : 0;
    const pageTitle = `Run #${run?.id ?? ""}`;
    const pageDescription = run ? `${run.profile_name} · ${run.source_keys.map(getSourceLabel).join(", ")}` : "";
    const searchesFinishedText = `${finishedSearches} / ${run?.tasks_total ?? 0}`;
    const websitesReadText = run && run.enrich_total > 0 ? `${run.enrich_done} / ${run.enrich_total}` : NO_VALUE;
    const startedText = run ? formatDateTime(run.started_at ?? run.created_at) : NO_VALUE;
    const finishedText = run?.finished_at ? formatDateTime(run.finished_at) : NO_VALUE;
    const hasBillableRequests = (run?.paid_requests_used ?? 0) > 0;
    const billableText = run
        ? `${formatCount(run.paid_requests_used)}${run.max_paid_requests !== null ? ` of ${formatCount(run.max_paid_requests)} allowed` : ""}`
        : "";
    const estimatedCostText = run ? `about ${formatUsd(run.estimated_cost_usd)}` : "";
    const canCancel = isActive && run?.status !== RUN_STATUS.CANCELLING;
    const failedText = formatCount(run?.tasks_failed ?? 0);
    const skippedText = formatCount(run?.tasks_skipped ?? 0);

    return {
        run,
        isLoading,
        isError,
        isActive,
        tasks,
        tasksTotal,
        isTasksLoading,
        taskPage,
        taskPageSize,
        taskStatus,
        statusLabel,
        statusClassName,
        finishedSearches,
        pageTitle,
        pageDescription,
        searchesFinishedText,
        websitesReadText,
        startedText,
        finishedText,
        hasBillableRequests,
        billableText,
        estimatedCostText,
        canCancel,
        failedText,
        skippedText,
        setTaskStatus,
        setTaskPage,
        showCancel,
        openCancel,
        closeCancel,
        handleCancel,
        isCancelling,
        handleResume,
        isResuming,
        canResume,
    };
};
