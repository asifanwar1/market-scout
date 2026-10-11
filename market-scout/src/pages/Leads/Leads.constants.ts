import { CRM_LAYOUT } from "@/constants/integration.constants";
import { SCORE_HIGH_MIN, SCORE_MEDIUM_MIN } from "@/constants/limits.constants";

export const LEAD_SORT = {
    SCORE: "score",
    NEWEST: "newest",
    LAST_SEEN: "last_seen",
    NAME: "name",
    AI_FIT: "ai_fit",
} as const;

export const SORT_VALUES = [LEAD_SORT.SCORE, LEAD_SORT.AI_FIT, LEAD_SORT.NEWEST, LEAD_SORT.LAST_SEEN, LEAD_SORT.NAME] as const;

export const SORT_DIRECTION = {
    ASC: "asc",
    DESC: "desc",
} as const;

export const DIRECTION_VALUES = [SORT_DIRECTION.ASC, SORT_DIRECTION.DESC] as const;

export const UNASSIGNED = "unassigned";

export const LEADS_PAGE_TITLE = "Leads";

export const LEADS_PAGE_DESCRIPTION = "Businesses to contact, best first. Click a row for details and to record what happened.";

export const EXPORT_FILE_PREFIX = "market-scout-leads-";

export const EXPORT_FORMAT = {
    CSV: "csv",
    XLSX: "xlsx",
} as const;

export const EXPORT_OPTIONS = [
    { format: EXPORT_FORMAT.CSV, label: "CSV (.csv)", extension: ".csv" },
    { format: EXPORT_FORMAT.XLSX, label: "Excel (.xlsx)", extension: ".xlsx" },
] as const;

export const EXPORT_BUTTON_LABEL = "Export";

export const CRM_EXPORT_HEADING = "For a CRM";

export const CRM_EXPORT_OPTIONS = [
    { layout: CRM_LAYOUT.HUBSPOT, label: "HubSpot companies (.csv)" },
    { layout: CRM_LAYOUT.ZOHO, label: "Zoho CRM leads (.csv)" },
    { layout: CRM_LAYOUT.GENERIC, label: "Any CRM, plain columns (.csv)" },
] as const;

export const SELECT_COLUMN_WIDTH = 40;
export const ACTIONS_COLUMN_WIDTH = 56;

export const DELETE_LEAD_TITLE = "Delete this lead?";
export const DELETE_LEAD_DESCRIPTION_SUFFIX =
    "will be permanently erased, along with its contact details, sources and history. This can't be undone, and a future run may find the business again as a new lead.";
export const DELETE_LEAD_CONFIRM_TEXT = "Delete lead";
export const DELETE_LEAD_ARIA_PREFIX = "Delete";

export const BULK_DELETE_TITLE = "Delete the selected leads?";
export const BULK_DELETE_DESCRIPTION_SUFFIX =
    "will be permanently erased, along with their contact details, sources and history. This can't be undone, and a future run may find the businesses again as new leads.";
export const BULK_DELETE_CONFIRM_TEXT = "Delete leads";
export const BULK_DELETE_BUTTON_LABEL = "Delete selected";

export const MIN_SCORES = [
    { value: String(SCORE_MEDIUM_MIN), label: `${SCORE_MEDIUM_MIN}+ (some contact detail)` },
    { value: String(SCORE_HIGH_MIN), label: `${SCORE_HIGH_MIN}+ (ready to call)` },
];

export const EMPTY_KIND = {
    NO_PROFILE: "no_profile",
    FILTERED: "filtered",
    NONE: "none",
} as const;

export const FILTER_FLAGS = [
    ["phone", "A phone number"],
    ["whatsapp", "A WhatsApp-capable number"],
    ["email", "An email address"],
    ["website", "A website"],
] as const;
