export const CRM_LAYOUT = {
    HUBSPOT: "hubspot",
    ZOHO: "zoho",
    GENERIC: "generic",
} as const;

export type CrmLayout = (typeof CRM_LAYOUT)[keyof typeof CRM_LAYOUT];

export const WEBHOOK_EVENT = {
    LEAD_CREATED: "lead.created",
    LEAD_STATUS_CHANGED: "lead.status_changed",
    ALERT_RAISED: "alert.raised",
    MESSAGE_SENT: "message.sent",
    PING: "ping",
} as const;

export type WebhookEvent = (typeof WEBHOOK_EVENT)[keyof typeof WEBHOOK_EVENT];

export const DELIVERY_STATUS = {
    QUEUED: "queued",
    RUNNING: "running",
    DELIVERED: "delivered",
    FAILED: "failed",
} as const;

export type DeliveryStatus = (typeof DELIVERY_STATUS)[keyof typeof DELIVERY_STATUS];

export const DELIVERY_STATUS_LABELS: Record<DeliveryStatus, string> = {
    [DELIVERY_STATUS.QUEUED]: "Waiting",
    [DELIVERY_STATUS.RUNNING]: "Sending",
    [DELIVERY_STATUS.DELIVERED]: "Delivered",
    [DELIVERY_STATUS.FAILED]: "Failed",
};

export const WEBHOOK_EVENT_LABELS: Record<WebhookEvent, string> = {
    [WEBHOOK_EVENT.LEAD_CREATED]: "New lead found",
    [WEBHOOK_EVENT.LEAD_STATUS_CHANGED]: "Lead status changed",
    [WEBHOOK_EVENT.ALERT_RAISED]: "Alert raised",
    [WEBHOOK_EVENT.MESSAGE_SENT]: "Message sent",
    [WEBHOOK_EVENT.PING]: "Test",
};

export const API_KEY_NAME_MAX_LENGTH = 100;
export const WEBHOOK_NAME_MAX_LENGTH = 100;
export const WEBHOOK_URL_MAX_LENGTH = 500;
