import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import {
    AddActivity,
    CreateTask,
    DeleteTask,
    GetActivities,
    GetPipelineConfig,
    GetTaskSummary,
    GetTasks,
    PIPELINE_QUERY_KEYS,
    UpdateTask,
} from "@/api";
import type {
    TActivityBody,
    TGetTasksParams,
    TTaskBody,
    TTaskUpdateBody,
} from "@/api/services/pipeline/pipeline.request.types";
import { REFERENCE_STALE_TIME } from "@/constants/timing.constants";
import { DRAWER_LIST_LIMIT, TASK_SUMMARY_REFETCH_MS } from "@/constants/pipeline.constants";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";

const DEFAULT_CURRENCY = "USD";

export const useGetPipelineConfig = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    const query = useQuery({
        queryKey: [PIPELINE_QUERY_KEYS.CONFIG],
        enabled: isAuthenticated,
        staleTime: REFERENCE_STALE_TIME,
        queryFn: GetPipelineConfig,
    });

    return query.data?.deal_currency ?? DEFAULT_CURRENCY;
};

export const useGetActivities = (businessId: number) => {
    return useQuery({
        queryKey: [PIPELINE_QUERY_KEYS.ACTIVITIES, businessId],
        queryFn: () => GetActivities({ id: businessId, params: { limit: DRAWER_LIST_LIMIT } }),
    });
};

export const useGetTasks = (params: TGetTasksParams, enabled = true) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [PIPELINE_QUERY_KEYS.TASKS, params],
        enabled: enabled && isAuthenticated,
        placeholderData: keepPreviousData,
        queryFn: () => GetTasks(params),
    });
};

export const useGetTaskSummary = (today: string) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [PIPELINE_QUERY_KEYS.TASK_SUMMARY, today],
        enabled: isAuthenticated,
        refetchInterval: TASK_SUMMARY_REFETCH_MS,
        queryFn: () => GetTaskSummary({ mine: true, today }),
    });
};

const refreshTasks = () =>
    invalidateMultiple(queryClient, [
        [PIPELINE_QUERY_KEYS.TASKS],
        [PIPELINE_QUERY_KEYS.TASK_SUMMARY],
        [PIPELINE_QUERY_KEYS.ACTIVITIES],
    ]);

export const useAddActivity = () => {
    return useMutation({
        mutationFn: ({ id, body }: { id: number; body: TActivityBody }) => AddActivity({ id, body }),
        onSuccess: () => invalidateMultiple(queryClient, [[PIPELINE_QUERY_KEYS.ACTIVITIES]]),
    });
};

export const useCreateTask = () => {
    return useMutation({
        mutationFn: ({ id, body }: { id: number; body: TTaskBody }) => CreateTask({ id, body }),
        onSuccess: refreshTasks,
    });
};

export const useUpdateTask = () => {
    return useMutation({
        mutationFn: ({ id, body }: { id: number; body: TTaskUpdateBody }) => UpdateTask({ id, body }),
        onSuccess: refreshTasks,
    });
};

export const useDeleteTask = () => {
    return useMutation({
        mutationFn: (id: number) => DeleteTask({ id }),
        onSuccess: refreshTasks,
    });
};
