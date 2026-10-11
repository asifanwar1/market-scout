export const OUTREACH_CHANNEL = {
    WHATSAPP: "whatsapp",
    EMAIL: "email",
} as const;

export type OutreachChannel = (typeof OUTREACH_CHANNEL)[keyof typeof OUTREACH_CHANNEL];

export const TEMPLATE_CHANNEL = {
    WHATSAPP: "whatsapp",
    EMAIL: "email",
    ANY: "any",
} as const;

export type TemplateChannel = (typeof TEMPLATE_CHANNEL)[keyof typeof TEMPLATE_CHANNEL];

export const MESSAGE_STATUS = {
    OPENED: "opened",
    SENT: "sent",
    NOT_SENT: "not_sent",
} as const;

export type MessageStatus = (typeof MESSAGE_STATUS)[keyof typeof MESSAGE_STATUS];

export const TEMPLATE_CHANNEL_LABELS: Record<TemplateChannel, string> = {
    [TEMPLATE_CHANNEL.WHATSAPP]: "WhatsApp",
    [TEMPLATE_CHANNEL.EMAIL]: "Email",
    [TEMPLATE_CHANNEL.ANY]: "Any channel",
};

export const MESSAGE_CHANNEL_LABELS: Record<OutreachChannel, string> = {
    [OUTREACH_CHANNEL.WHATSAPP]: "WhatsApp",
    [OUTREACH_CHANNEL.EMAIL]: "Email",
};

export const MESSAGE_STATUS_LABELS: Record<MessageStatus, string> = {
    [MESSAGE_STATUS.OPENED]: "Opened, not confirmed",
    [MESSAGE_STATUS.SENT]: "Sent",
    [MESSAGE_STATUS.NOT_SENT]: "Not sent",
};

export const TEMPLATE_CHANNEL_OPTIONS = [
    { value: TEMPLATE_CHANNEL.WHATSAPP, label: TEMPLATE_CHANNEL_LABELS[TEMPLATE_CHANNEL.WHATSAPP] },
    { value: TEMPLATE_CHANNEL.EMAIL, label: TEMPLATE_CHANNEL_LABELS[TEMPLATE_CHANNEL.EMAIL] },
    { value: TEMPLATE_CHANNEL.ANY, label: TEMPLATE_CHANNEL_LABELS[TEMPLATE_CHANNEL.ANY] },
] as const;

export const MESSAGE_STATUS_OPTIONS = [
    { value: MESSAGE_STATUS.SENT, label: MESSAGE_STATUS_LABELS[MESSAGE_STATUS.SENT] },
    { value: MESSAGE_STATUS.NOT_SENT, label: MESSAGE_STATUS_LABELS[MESSAGE_STATUS.NOT_SENT] },
    { value: MESSAGE_STATUS.OPENED, label: MESSAGE_STATUS_LABELS[MESSAGE_STATUS.OPENED] },
] as const;

export const TEMPLATE_NAME_MAX_LENGTH = 100;
export const CONTACT_NAME_MAX_LENGTH = 100;
