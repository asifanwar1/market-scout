import type { TListResponse } from "@/api/types/common";
import type { DeliveryStatus, WebhookEvent } from "@/constants/integration.constants";

export type TEventInfo = {
    key: WebhookEvent;
    label: string;
    description: string;
};

export type TWebhookConfig = {
    events: TEventInfo[];
    max_attempts: number;
    disable_after_failures: number;
    allow_private_urls: boolean;
};

export type TWebhook = {
    id: number;
    name: string;
    url: string;
    events: WebhookEvent[];
    is_active: boolean;
    consecutive_failures: number;
    last_delivery_at: string | null;
    last_status_code: number | null;
    last_error: string | null;
    secret_hint: string;
    created_at: string;
};

export type TWebhookCreated = TWebhook & {
    secret: string;
};

export type TGetWebhooksResponse = TListResponse<TWebhook>;

export type TDelivery = {
    id: number;
    webhook_id: number;
    event: WebhookEvent;
    status: DeliveryStatus;
    attempts: number;
    next_attempt_at: string | null;
    response_status: number | null;
    error: string | null;
    created_at: string;
    delivered_at: string | null;
};

export type TGetDeliveriesResponse = TListResponse<TDelivery>;
