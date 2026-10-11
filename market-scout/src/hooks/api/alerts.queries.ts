import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import { ALERT_QUERY_KEYS, GetAlertSettings, GetAlertSummary, GetAlerts, MarkAlertsRead, UpdateAlertSettings } from "@/api";
import type { TAlertSettingsBody, TGetAlertsParams, TMarkReadBody } from "@/api/services/alerts/alerts.request.types";
import { ALERTS_POLL_MS } from "@/constants/timing.constants";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";

export const useGetAlerts = (params: TGetAlertsParams) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [ALERT_QUERY_KEYS.ALERTS, params],
        enabled: isAuthenticated,
        placeholderData: keepPreviousData,
        queryFn: () => GetAlerts(params),
    });
};

export const useGetAlertSummary = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [ALERT_QUERY_KEYS.SUMMARY],
        enabled: isAuthenticated,
        queryFn: GetAlertSummary,
        refetchInterval: ALERTS_POLL_MS,
    });
};

export const useMarkAlertsRead = () => {
    return useMutation({
        mutationFn: (body: TMarkReadBody) => MarkAlertsRead(body),
        onSuccess: (summary) => {
            queryClient.setQueryData([ALERT_QUERY_KEYS.SUMMARY], summary);
            return invalidateMultiple(queryClient, [[ALERT_QUERY_KEYS.ALERTS]]);
        },
    });
};

export const useGetAlertSettings = (enabled: boolean) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [ALERT_QUERY_KEYS.SETTINGS],
        enabled: enabled && isAuthenticated,
        queryFn: GetAlertSettings,
    });
};

export const useUpdateAlertSettings = () => {
    return useMutation({
        mutationFn: (body: TAlertSettingsBody) => UpdateAlertSettings(body),
        onSuccess: (settings) => {
            queryClient.setQueryData([ALERT_QUERY_KEYS.SETTINGS], settings);
        },
    });
};
