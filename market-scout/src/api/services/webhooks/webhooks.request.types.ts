import type { WebhookEvent } from "@/constants/integration.constants";

export type TWebhookBody = {
    name: string;
    url: string;
    events: WebhookEvent[];
};

export type TWebhookUpdateBody = Partial<TWebhookBody> & {
    is_active?: boolean;
};

export type TGetDeliveriesParams = {
    page?: number;
    limit?: number;
};
