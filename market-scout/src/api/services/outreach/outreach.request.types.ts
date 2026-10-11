import type { MessageStatus, OutreachChannel, TemplateChannel } from "@/constants/outreach.constants";

export type TGetTemplatesParams = {
    channel?: TemplateChannel;
};

export type TTemplateBody = {
    name: string;
    channel: TemplateChannel;
    subject?: string | null;
    body: string;
};

export type TTemplateUpdateBody = Partial<TTemplateBody>;

export type TPreviewBody = {
    business_id: number;
    template_id?: number;
    subject?: string | null;
    body?: string;
};

export type TPrepareBody = {
    business_id: number;
    contact_id: number;
    channel: OutreachChannel;
    template_id?: number;
    subject?: string | null;
    body: string;
};

export type TDecisionBody = {
    sent: boolean;
};

export type TGetMessagesParams = {
    business_id?: number;
    mine?: boolean;
    status?: MessageStatus;
    page?: number;
    limit?: number;
};
