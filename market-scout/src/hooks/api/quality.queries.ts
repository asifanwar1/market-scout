import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import {
    ApplyScoring,
    BUSINESS_QUERY_KEYS,
    DismissDuplicate,
    GetDuplicates,
    GetQualitySettings,
    GetQualityTask,
    GetScoring,
    MergeDuplicate,
    PROFILE_QUERY_KEYS,
    QUALITY_QUERY_KEYS,
    RevertScoring,
    ScanDuplicates,
    StartChecks,
    UpdateQualitySettings,
} from "@/api";
import type {
    TCheckBody,
    TGetDuplicatesParams,
    TMergeBody,
    TQualitySettingsBody,
    TScoringProfileBody,
} from "@/api/services/quality/quality.request.types";
import { ACTIVE_QUALITY_TASK_STATUSES } from "@/constants/quality.constants";
import { FAST_POLL_MS } from "@/constants/timing.constants";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";

const refreshLeads = () => invalidateMultiple(queryClient, [[BUSINESS_QUERY_KEYS.BUSINESSES], [BUSINESS_QUERY_KEYS.BUSINESS]]);

const refreshDuplicates = () => invalidateMultiple(queryClient, [[QUALITY_QUERY_KEYS.DUPLICATES]]);

export const useStartChecks = () => {
    return useMutation({ mutationFn: (body: TCheckBody) => StartChecks(body) });
};

export const useGetQualityTask = (id: number | null) => {
    return useQuery({
        queryKey: [QUALITY_QUERY_KEYS.TASK, id],
        enabled: id !== null,
        queryFn: async () => {
            const task = await GetQualityTask({ id: id as number });
            if (!ACTIVE_QUALITY_TASK_STATUSES.includes(task.status)) {
                void refreshLeads();
                void refreshDuplicates();
            }
            return task;
        },
        refetchInterval: (query) =>
            query.state.data && ACTIVE_QUALITY_TASK_STATUSES.includes(query.state.data.status) ? FAST_POLL_MS : false,
    });
};

export const useGetDuplicates = (params: TGetDuplicatesParams) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [QUALITY_QUERY_KEYS.DUPLICATES, params],
        enabled: isAuthenticated,
        placeholderData: keepPreviousData,
        queryFn: () => GetDuplicates(params),
    });
};

export const useScanDuplicates = () => {
    return useMutation({ mutationFn: ScanDuplicates });
};

export const useMergeDuplicate = () => {
    return useMutation({
        mutationFn: ({ id, body }: { id: number; body: TMergeBody }) => MergeDuplicate({ id, body }),
        onSuccess: async () => {
            await refreshDuplicates();
            await refreshLeads();
        },
    });
};

export const useDismissDuplicate = () => {
    return useMutation({
        mutationFn: (id: number) => DismissDuplicate({ id }),
        onSuccess: refreshDuplicates,
    });
};

export const useGetScoring = (profileId: number | undefined) => {
    return useQuery({
        queryKey: [QUALITY_QUERY_KEYS.SCORING, profileId],
        enabled: profileId !== undefined,
        queryFn: () => GetScoring(profileId as number),
    });
};

const refreshAfterWeights = () =>
    invalidateMultiple(queryClient, [
        [QUALITY_QUERY_KEYS.SCORING],
        [PROFILE_QUERY_KEYS.PROFILES],
        [PROFILE_QUERY_KEYS.PROFILE],
        [BUSINESS_QUERY_KEYS.BUSINESSES],
        [BUSINESS_QUERY_KEYS.BUSINESS],
    ]);

export const useApplyScoring = () => {
    return useMutation({
        mutationFn: (body: TScoringProfileBody) => ApplyScoring(body),
        onSuccess: refreshAfterWeights,
    });
};

export const useRevertScoring = () => {
    return useMutation({
        mutationFn: (body: TScoringProfileBody) => RevertScoring(body),
        onSuccess: refreshAfterWeights,
    });
};

export const useGetQualitySettings = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [QUALITY_QUERY_KEYS.SETTINGS],
        enabled: isAuthenticated,
        queryFn: GetQualitySettings,
    });
};

export const useUpdateQualitySettings = () => {
    return useMutation({
        mutationFn: (body: TQualitySettingsBody) => UpdateQualitySettings(body),
        onSuccess: (settings) => {
            queryClient.setQueryData([QUALITY_QUERY_KEYS.SETTINGS], settings);
        },
    });
};
