import type { TContactPoint } from "@/api/services/businesses/businesses.response.types";
import type { TMessageTemplate, TOutreachMessage, TPlaceholder } from "@/api/services/outreach/outreach.response.types";
import {
    MESSAGE_CHANNEL_LABELS,
    MESSAGE_STATUS_LABELS,
    OUTREACH_CHANNEL,
    TEMPLATE_CHANNEL,
    type MessageStatus,
    type OutreachChannel,
    type TemplateChannel,
} from "@/constants/outreach.constants";
import { CHECK_STATUS } from "@/constants/quality.constants";
import { CONTACT_KIND } from "@/constants/source.constants";

const PLACEHOLDER_OPEN = "{";
const PLACEHOLDER_CLOSE = "}";
const SPACE = " ";
const NEWLINE = "\n";
const MESSAGE_PREVIEW_LENGTH = 90;
const ELLIPSIS = "…";
const DOT_SEPARATOR = " · ";

export const placeholderToken = (key: string): string => `${PLACEHOLDER_OPEN}${key}${PLACEHOLDER_CLOSE}`;

export const appendPlaceholder = (text: string, key: string): string => {
    const separator = text === "" || text.endsWith(SPACE) || text.endsWith(NEWLINE) ? "" : SPACE;
    return `${text}${separator}${placeholderToken(key)}`;
};

export const describePlaceholder = (placeholder: TPlaceholder): string =>
    placeholder.fallback === null ? placeholder.label : `${placeholder.label} (says "${placeholder.fallback}" if unknown)`;

export const templatesForChannel = (templates: TMessageTemplate[], channel: OutreachChannel): TMessageTemplate[] =>
    templates.filter((template) => template.channel === channel || template.channel === TEMPLATE_CHANNEL.ANY);

const rankContact = (contact: TContactPoint): number => {
    if (contact.kind === CONTACT_KIND.WHATSAPP) return 0;
    if (contact.whatsapp_likely) return 1;
    return contact.is_mobile ? 2 : 3;
};

export const contactsForChannel = (contacts: TContactPoint[], channel: OutreachChannel): TContactPoint[] => {
    const usable =
        channel === OUTREACH_CHANNEL.EMAIL
            ? contacts.filter((contact) => contact.kind === CONTACT_KIND.EMAIL && contact.check_status !== CHECK_STATUS.BAD)
            : contacts.filter((contact) => contact.kind === CONTACT_KIND.PHONE || contact.kind === CONTACT_KIND.WHATSAPP);
    return [...usable].sort((a, b) => rankContact(a) - rankContact(b) || a.id - b.id);
};

export const supportsSubject = (channel: TemplateChannel): boolean => channel !== TEMPLATE_CHANNEL.WHATSAPP;

export const channelLabel = (channel: OutreachChannel): string => MESSAGE_CHANNEL_LABELS[channel];

export const statusLabel = (status: MessageStatus): string => MESSAGE_STATUS_LABELS[status];

export const previewText = (text: string): string => {
    const flat = text.replace(/\s+/g, SPACE).trim();
    return flat.length > MESSAGE_PREVIEW_LENGTH ? `${flat.slice(0, MESSAGE_PREVIEW_LENGTH)}${ELLIPSIS}` : flat;
};

export const describeMessage = (message: TOutreachMessage, target: string): string =>
    [channelLabel(message.channel), target, message.template_name].filter(Boolean).join(DOT_SEPARATOR);
