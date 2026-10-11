import type { TListResponse } from "@/api/types/common";
import type { MessageStatus, OutreachChannel, TemplateChannel } from "@/constants/outreach.constants";

export type TPlaceholder = {
    key: string;
    label: string;
    fallback: string | null;
};

export type TOutreachConfig = {
    placeholders: TPlaceholder[];
    template_channels: TemplateChannel[];
    subject_max_length: number;
    body_max_length: number;
    recent_days: number;
};

export type TMessageTemplate = {
    id: number;
    name: string;
    channel: TemplateChannel;
    subject: string | null;
    body: string;
    created_at: string;
    updated_at: string | null;
};

export type TGetTemplatesResponse = TListResponse<TMessageTemplate>;

export type TPreview = {
    subject: string | null;
    body: string;
};

export type TPerson = {
    id: number;
    full_name: string;
};

export type TPreparedMessage = {
    id: number;
    channel: OutreachChannel;
    to_value: string;
    subject: string | null;
    body: string;
    link: string;
    last_sent_at: string | null;
    last_sent_by: TPerson | null;
};

export type TOutreachMessage = {
    id: number;
    business_id: number;
    business_name: string;
    template_name: string | null;
    channel: OutreachChannel;
    to_value: string;
    subject: string | null;
    body: string;
    status: MessageStatus;
    created_by: TPerson | null;
    created_at: string;
    decided_at: string | null;
};

export type TGetMessagesResponse = TListResponse<TOutreachMessage>;
