import {
    keepPreviousData,
    useMutation,
    useQuery,
} from "@tanstack/react-query";

import {
    CancelRun,
    CreateRun,
    EstimateRun,
    GetRun,
    GetRuns,
    GetRunTasks,
    ResumeRun,
    RUN_QUERY_KEYS,
} from "@/api";
import type {
    TCreateRunBody,
    TGetRunsParams,
    TGetRunTasksParams,
} from "@/api/services/runs/runs.request.types";
import { ACTIVE_RUN_STATUSES } from "@/constants/run-status.constants";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";
import { RUN_POLL_MS } from "@/constants/timing.constants";


export const useGetRuns = (params: TGetRunsParams) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [RUN_QUERY_KEYS.RUNS, params],
        enabled: isAuthenticated,
        placeholderData: keepPreviousData,
        queryFn: () => GetRuns(params),
        refetchInterval: (query) =>
            query.state.data?.data.some((run) =>
                ACTIVE_RUN_STATUSES.includes(run.status),
            )
                ? RUN_POLL_MS
                : false,
    });
};

export const useGetRun = (id?: number) => {
    return useQuery({
        queryKey: [RUN_QUERY_KEYS.RUN, id],
        enabled: !!id,
        queryFn: () => GetRun({ id: id as number }),
        refetchInterval: (query) =>
            query.state.data && ACTIVE_RUN_STATUSES.includes(query.state.data.status)
                ? RUN_POLL_MS
                : false,
    });
};

export const useGetRunTasks = (
    id: number | undefined,
    params: TGetRunTasksParams,
    isActive: boolean,
) => {
    return useQuery({
        queryKey: [RUN_QUERY_KEYS.RUN_TASKS, id, params],
        enabled: !!id,
        placeholderData: keepPreviousData,
        queryFn: () => GetRunTasks({ id: id as number, params }),
        refetchInterval: isActive ? RUN_POLL_MS : false,
    });
};

export const useEstimateRun = (body: TCreateRunBody | null) => {
    return useQuery({
        queryKey: [RUN_QUERY_KEYS.RUN_ESTIMATE, body],
        enabled: body !== null,
        placeholderData: keepPreviousData,
        retry: false,
        queryFn: ({ signal }) => EstimateRun({ ...(body as TCreateRunBody), signal }),
    });
};

const refreshRuns = () =>
    invalidateMultiple(queryClient, [
        [RUN_QUERY_KEYS.RUNS],
        [RUN_QUERY_KEYS.RUN],
        [RUN_QUERY_KEYS.RUN_TASKS],
    ]);

export const useCreateRun = () => {
    return useMutation({
        mutationFn: (body: TCreateRunBody) => CreateRun(body),
        onSuccess: refreshRuns,
    });
};

export const useCancelRun = () => {
    return useMutation({
        mutationFn: (id: number) => CancelRun({ id }),
        onSuccess: refreshRuns,
    });
};

export const useResumeRun = () => {
    return useMutation({
        mutationFn: (id: number) => ResumeRun({ id }),
        onSuccess: refreshRuns,
    });
};
