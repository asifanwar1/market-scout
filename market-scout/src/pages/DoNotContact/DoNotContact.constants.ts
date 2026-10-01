export const DO_NOT_CONTACT_KIND = {
    BUSINESS: "business",
    PHONE: "phone",
    EMAIL: "email",
} as const;

export const KIND_LABELS = {
    [DO_NOT_CONTACT_KIND.BUSINESS]: "Business",
    [DO_NOT_CONTACT_KIND.PHONE]: "Phone",
    [DO_NOT_CONTACT_KIND.EMAIL]: "Email",
} as const;

export const DO_NOT_CONTACT_PAGE_TITLE = "Do not contact";

export const DO_NOT_CONTACT_PAGE_DESCRIPTION =
    "People and numbers that asked not to be contacted. They're hidden from Leads and skipped by every run.";

export const NO_SEARCH_MATCH_TITLE = "Nothing matches that search";
export const EMPTY_LIST_TITLE = "Nobody is on the list";
export const EMPTY_LIST_DESCRIPTION =
    "When a business asks not to be contacted, mark it from its lead panel, or add a phone number or email here.";

export const LIFT_BUSINESS_DESCRIPTION_SUFFIX = "and its phone numbers and emails will appear in Leads again and can be updated by future runs.";
export const LIFT_IDENTIFIER_DESCRIPTION = "Whoever owns it can appear in Leads again and be added by future runs.";

export const PLUS_SIGN = "+";
export const ACTIONS_COLUMN_WIDTH = 120;
export const REASON_MAX_LENGTH = 500;
export const EMPTY_REASON_PLACEHOLDER = "—";
