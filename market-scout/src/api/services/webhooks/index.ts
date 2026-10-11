import { request } from "@/api/client/request";
import type { TApiArgs, TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import { ENDPOINTS } from "@/constants/endpoints.constants";
import type { TGetDeliveriesParams, TWebhookBody, TWebhookUpdateBody } from "./webhooks.request.types";
import type {
    TDelivery,
    TGetDeliveriesResponse,
    TGetWebhooksResponse,
    TWebhook,
    TWebhookConfig,
    TWebhookCreated,
} from "./webhooks.response.types";
import { WEBHOOK_QUERY_KEYS } from "./queryKeys";

export const GetWebhookConfig = () => request<TWebhookConfig>({ method: HTTP_METHODS.GET, url: ENDPOINTS.WEBHOOKS.CONFIG });

export const GetWebhooks = () => request<TGetWebhooksResponse>({ method: HTTP_METHODS.GET, url: ENDPOINTS.WEBHOOKS.ROOT });

export const CreateWebhook = (body: TWebhookBody) =>
    request<TWebhookCreated, TWebhookBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.WEBHOOKS.ROOT, body });

export const UpdateWebhook = ({ id, body }: TApiArgs<TWebhookUpdateBody>) =>
    request<TWebhook, TWebhookUpdateBody>({ method: HTTP_METHODS.PATCH, url: ENDPOINTS.WEBHOOKS.hook(id), body });

export const DeleteWebhook = ({ id }: TApiArgs) => request<void>({ method: HTTP_METHODS.DELETE, url: ENDPOINTS.WEBHOOKS.hook(id) });

export const RotateWebhookSecret = ({ id }: TApiArgs) =>
    request<TWebhookCreated>({ method: HTTP_METHODS.POST, url: ENDPOINTS.WEBHOOKS.rotateSecret(id) });

export const SendWebhookTest = ({ id }: TApiArgs) =>
    request<TDelivery>({ method: HTTP_METHODS.POST, url: ENDPOINTS.WEBHOOKS.test(id) });

export const GetDeliveries = ({ id, params }: TApiArgs<undefined, TGetDeliveriesParams>) =>
    request<TGetDeliveriesResponse>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.WEBHOOKS.deliveries(id),
        params: params as TQueryParams,
        silent: true,
    });

export const RetryDelivery = ({ id }: TApiArgs) =>
    request<TDelivery>({ method: HTTP_METHODS.POST, url: ENDPOINTS.WEBHOOKS.retry(id) });

export { WEBHOOK_QUERY_KEYS };
