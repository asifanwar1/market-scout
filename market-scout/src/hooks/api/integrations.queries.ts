import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import {
    API_KEY_QUERY_KEYS,
    CreateApiKey,
    CreateWebhook,
    DeleteWebhook,
    GetApiKeys,
    GetDeliveries,
    GetWebhookConfig,
    GetWebhooks,
    RetryDelivery,
    RevokeApiKey,
    RotateWebhookSecret,
    SendWebhookTest,
    UpdateWebhook,
    WEBHOOK_QUERY_KEYS,
} from "@/api";
import type { TApiKeyBody } from "@/api/services/apiKeys/apiKeys.request.types";
import type { TGetDeliveriesParams, TWebhookBody, TWebhookUpdateBody } from "@/api/services/webhooks/webhooks.request.types";
import { REFERENCE_STALE_TIME } from "@/constants/timing.constants";
import { DELIVERY_STATUS } from "@/constants/integration.constants";
import { FAST_POLL_MS } from "@/constants/timing.constants";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";

const refreshKeys = () => invalidateMultiple(queryClient, [[API_KEY_QUERY_KEYS.KEYS]]);

const refreshWebhooks = () => invalidateMultiple(queryClient, [[WEBHOOK_QUERY_KEYS.WEBHOOKS]]);

const refreshDeliveries = () => invalidateMultiple(queryClient, [[WEBHOOK_QUERY_KEYS.DELIVERIES], [WEBHOOK_QUERY_KEYS.WEBHOOKS]]);

export const useGetApiKeys = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [API_KEY_QUERY_KEYS.KEYS],
        enabled: isAuthenticated,
        queryFn: GetApiKeys,
    });
};

export const useCreateApiKey = () => {
    return useMutation({ mutationFn: (body: TApiKeyBody) => CreateApiKey(body), onSuccess: refreshKeys });
};

export const useRevokeApiKey = () => {
    return useMutation({ mutationFn: (id: number) => RevokeApiKey({ id }), onSuccess: refreshKeys });
};

export const useGetWebhookConfig = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [WEBHOOK_QUERY_KEYS.CONFIG],
        enabled: isAuthenticated,
        staleTime: REFERENCE_STALE_TIME,
        queryFn: GetWebhookConfig,
    });
};

export const useGetWebhooks = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [WEBHOOK_QUERY_KEYS.WEBHOOKS],
        enabled: isAuthenticated,
        queryFn: GetWebhooks,
    });
};

export const useCreateWebhook = () => {
    return useMutation({ mutationFn: (body: TWebhookBody) => CreateWebhook(body), onSuccess: refreshWebhooks });
};

export const useUpdateWebhook = () => {
    return useMutation({
        mutationFn: ({ id, body }: { id: number; body: TWebhookUpdateBody }) => UpdateWebhook({ id, body }),
        onSuccess: refreshWebhooks,
    });
};

export const useDeleteWebhook = () => {
    return useMutation({ mutationFn: (id: number) => DeleteWebhook({ id }), onSuccess: refreshWebhooks });
};

export const useRotateWebhookSecret = () => {
    return useMutation({ mutationFn: (id: number) => RotateWebhookSecret({ id }), onSuccess: refreshWebhooks });
};

export const useSendWebhookTest = () => {
    return useMutation({ mutationFn: (id: number) => SendWebhookTest({ id }), onSuccess: refreshDeliveries });
};

export const useRetryDelivery = () => {
    return useMutation({ mutationFn: (id: number) => RetryDelivery({ id }), onSuccess: refreshDeliveries });
};

export const useGetDeliveries = (id: number | null, params: TGetDeliveriesParams) => {
    return useQuery({
        queryKey: [WEBHOOK_QUERY_KEYS.DELIVERIES, id, params],
        enabled: id !== null,
        placeholderData: keepPreviousData,
        queryFn: () => GetDeliveries({ id: id as number, params }),
        refetchInterval: (query) =>
            query.state.data?.data.some((item) => item.status === DELIVERY_STATUS.QUEUED || item.status === DELIVERY_STATUS.RUNNING)
                ? FAST_POLL_MS
                : false,
    });
};
