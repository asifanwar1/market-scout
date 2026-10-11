import { request } from "@/api/client/request";
import type { TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import { ENDPOINTS } from "@/constants/endpoints.constants";
import type { TAlertSettingsBody, TGetAlertsParams, TMarkReadBody } from "./alerts.request.types";
import type { TAlertSettings, TAlertSummary, TGetAlertsResponse } from "./alerts.response.types";
import { ALERT_QUERY_KEYS } from "./queryKeys";

export const GetAlerts = (params?: TGetAlertsParams) =>
    request<TGetAlertsResponse>({ method: HTTP_METHODS.GET, url: ENDPOINTS.ALERTS.ROOT, params: params as TQueryParams });

export const GetAlertSummary = () =>
    request<TAlertSummary>({ method: HTTP_METHODS.GET, url: ENDPOINTS.ALERTS.SUMMARY, silent: true });

export const MarkAlertsRead = (body: TMarkReadBody) =>
    request<TAlertSummary, TMarkReadBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.ALERTS.MARK_READ, body });

export const GetAlertSettings = () => request<TAlertSettings>({ method: HTTP_METHODS.GET, url: ENDPOINTS.ALERTS.SETTINGS });

export const UpdateAlertSettings = (body: TAlertSettingsBody) =>
    request<TAlertSettings, TAlertSettingsBody>({ method: HTTP_METHODS.PUT, url: ENDPOINTS.ALERTS.SETTINGS, body });

export { ALERT_QUERY_KEYS };
