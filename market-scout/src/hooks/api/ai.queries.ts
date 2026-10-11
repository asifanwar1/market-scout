import { useMutation, useQuery } from "@tanstack/react-query";

import {
    AI_QUERY_KEYS,
    ApplyAiSegment,
    BUSINESS_QUERY_KEYS,
    EstimateAi,
    GetAiBatch,
    GetAiSettings,
    GetAiStatus,
    PIPELINE_QUERY_KEYS,
    StartAiAnalysis,
    TestAi,
    UpdateAiSettings,
} from "@/api";
import type { TAiEstimateBody, TAiSettingsBody, TApplySegmentBody } from "@/api/services/ai/ai.request.types";
import { ACTIVE_AI_BATCH_STATUSES } from "@/constants/ai.constants";
import { FAST_POLL_MS } from "@/constants/timing.constants";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";

const refreshAfterAnalysis = () =>
    invalidateMultiple(queryClient, [
        [BUSINESS_QUERY_KEYS.BUSINESSES],
        [BUSINESS_QUERY_KEYS.BUSINESS],
        [AI_QUERY_KEYS.SETTINGS],
        [AI_QUERY_KEYS.STATUS],
    ]);

export const useGetAiSettings = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [AI_QUERY_KEYS.SETTINGS],
        enabled: isAuthenticated,
        queryFn: GetAiSettings,
    });
};

export const useUpdateAiSettings = () => {
    return useMutation({
        mutationFn: (body: TAiSettingsBody) => UpdateAiSettings(body),
        onSuccess: (settings) => {
            queryClient.setQueryData([AI_QUERY_KEYS.SETTINGS], settings);
            return invalidateMultiple(queryClient, [[AI_QUERY_KEYS.STATUS]]);
        },
    });
};

export const useTestAi = () => {
    return useMutation({ mutationFn: TestAi });
};

export const useGetAiStatus = (enabled = true) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [AI_QUERY_KEYS.STATUS],
        enabled: enabled && isAuthenticated,
        queryFn: GetAiStatus,
    });
};

export const useEstimateAi = (body: TAiEstimateBody | null) => {
    return useQuery({
        queryKey: [AI_QUERY_KEYS.ESTIMATE, body],
        enabled: body !== null,
        queryFn: () => EstimateAi(body as TAiEstimateBody),
    });
};

export const useStartAiAnalysis = () => {
    return useMutation({ mutationFn: (body: TAiEstimateBody) => StartAiAnalysis(body) });
};

export const useGetAiBatch = (batchId: number | null) => {
    return useQuery({
        queryKey: [AI_QUERY_KEYS.BATCH, batchId],
        enabled: batchId !== null,
        refetchInterval: (query) => {
            const status = query.state.data?.status;
            return status && !ACTIVE_AI_BATCH_STATUSES.includes(status) ? false : FAST_POLL_MS;
        },
        queryFn: async () => {
            const batch = await GetAiBatch({ id: batchId as number });
            if (!ACTIVE_AI_BATCH_STATUSES.includes(batch.status)) void refreshAfterAnalysis();
            return batch;
        },
    });
};

export const useApplyAiSegment = () => {
    return useMutation({
        mutationFn: ({ id, body }: { id: number; body: TApplySegmentBody }) => ApplyAiSegment({ id, body }),
        onSuccess: () =>
            invalidateMultiple(queryClient, [
                [BUSINESS_QUERY_KEYS.BUSINESSES],
                [BUSINESS_QUERY_KEYS.BUSINESS],
                [PIPELINE_QUERY_KEYS.ACTIVITIES],
            ]),
    });
};
