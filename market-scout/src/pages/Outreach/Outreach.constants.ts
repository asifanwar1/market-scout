import { MESSAGE_STATUS } from "@/constants/outreach.constants";

export const OUTREACH_PAGE_TITLE = "Outreach";

export const OUTREACH_PAGE_DESCRIPTION =
    "Message templates and a record of what your team sent. Messages open in WhatsApp or your mail app and you press send yourself; the app never sends anything on its own.";

export const TEMPLATES_TITLE = "Message templates";

export const TEMPLATES_DESCRIPTION =
    "Everyone can use these from a lead's Message button. Only admins can add, change or delete them.";

export const TEMPLATES_EMPTY_TITLE = "No templates yet";

export const TEMPLATES_EMPTY_ADMIN = "Add a first template so the team can message leads quickly.";

export const TEMPLATES_EMPTY_OTHER = "Ask an admin to add a template. You can still write a message by hand from a lead.";

export const LOG_TITLE = "Send log";

export const LOG_DESCRIPTION = "Only messages you confirmed as sent count as contacted and appear on the lead's history.";

export const LOG_EMPTY_TITLE = "Nothing sent yet";

export const LOG_EMPTY_DESCRIPTION = "Open a lead and press Message. Messages you open and confirm show up here.";

export const LOG_FILTER_STATUS_VALUES = [MESSAGE_STATUS.SENT, MESSAGE_STATUS.NOT_SENT, MESSAGE_STATUS.OPENED] as const;

export const DELETE_TEMPLATE_TITLE = "Delete this template?";

export const DELETE_TEMPLATE_DESCRIPTION = "Messages already sent keep their text and the template's name in the log.";
