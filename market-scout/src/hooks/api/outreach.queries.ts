import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import {
    BUSINESS_QUERY_KEYS,
    CreateTemplate,
    DecideMessage,
    DeleteTemplate,
    GetMessages,
    GetOutreachConfig,
    GetTemplates,
    OUTREACH_QUERY_KEYS,
    PIPELINE_QUERY_KEYS,
    PrepareMessage,
    PreviewMessage,
    UpdateTemplate,
} from "@/api";
import type {
    TDecisionBody,
    TGetMessagesParams,
    TGetTemplatesParams,
    TPrepareBody,
    TPreviewBody,
    TTemplateBody,
    TTemplateUpdateBody,
} from "@/api/services/outreach/outreach.request.types";
import { REFERENCE_STALE_TIME } from "@/constants/timing.constants";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";

const refreshTemplates = () => invalidateMultiple(queryClient, [[OUTREACH_QUERY_KEYS.TEMPLATES]]);

export const useGetOutreachConfig = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [OUTREACH_QUERY_KEYS.CONFIG],
        enabled: isAuthenticated,
        staleTime: REFERENCE_STALE_TIME,
        queryFn: GetOutreachConfig,
    });
};

export const useGetTemplates = (params: TGetTemplatesParams = {}) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [OUTREACH_QUERY_KEYS.TEMPLATES, params],
        enabled: isAuthenticated,
        queryFn: () => GetTemplates(params),
    });
};

export const useCreateTemplate = () => {
    return useMutation({
        mutationFn: (body: TTemplateBody) => CreateTemplate(body),
        onSuccess: refreshTemplates,
    });
};

export const useUpdateTemplate = () => {
    return useMutation({
        mutationFn: ({ id, body }: { id: number; body: TTemplateUpdateBody }) => UpdateTemplate({ id, body }),
        onSuccess: refreshTemplates,
    });
};

export const useDeleteTemplate = () => {
    return useMutation({
        mutationFn: (id: number) => DeleteTemplate({ id }),
        onSuccess: async () => {
            await refreshTemplates();
            await invalidateMultiple(queryClient, [[OUTREACH_QUERY_KEYS.MESSAGES]]);
        },
    });
};

export const usePreviewMessage = () => {
    return useMutation({ mutationFn: (body: TPreviewBody) => PreviewMessage(body) });
};

export const usePrepareMessage = () => {
    return useMutation({
        mutationFn: (body: TPrepareBody) => PrepareMessage(body),
        onSuccess: () => invalidateMultiple(queryClient, [[OUTREACH_QUERY_KEYS.MESSAGES]]),
    });
};

export const useDecideMessage = () => {
    return useMutation({
        mutationFn: ({ id, body }: { id: number; body: TDecisionBody }) => DecideMessage({ id, body }),
        onSuccess: () =>
            invalidateMultiple(queryClient, [
                [OUTREACH_QUERY_KEYS.MESSAGES],
                [PIPELINE_QUERY_KEYS.ACTIVITIES],
                [BUSINESS_QUERY_KEYS.BUSINESSES],
                [BUSINESS_QUERY_KEYS.BUSINESS],
            ]),
    });
};

export const useGetMessages = (params: TGetMessagesParams) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [OUTREACH_QUERY_KEYS.MESSAGES, params],
        enabled: isAuthenticated,
        placeholderData: keepPreviousData,
        queryFn: () => GetMessages(params),
    });
};
