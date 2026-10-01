import { SCORE_HIGH_MIN, SCORE_MEDIUM_MIN } from "@/constants/limits.constants";

export const LEAD_SORT = {
    SCORE: "score",
    NEWEST: "newest",
    LAST_SEEN: "last_seen",
    NAME: "name",
} as const;

export const SORT_VALUES = [LEAD_SORT.SCORE, LEAD_SORT.NEWEST, LEAD_SORT.LAST_SEEN, LEAD_SORT.NAME] as const;

export const SORT_DIRECTION = {
    ASC: "asc",
    DESC: "desc",
} as const;

export const DIRECTION_VALUES = [SORT_DIRECTION.ASC, SORT_DIRECTION.DESC] as const;

export const UNASSIGNED = "unassigned";

export const LEADS_PAGE_TITLE = "Leads";

export const LEADS_PAGE_DESCRIPTION = "Businesses to contact, best first. Click a row for details and to record what happened.";

export const EXPORT_FILE_PREFIX = "market-scout-leads-";
export const EXPORT_FILE_EXTENSION = ".csv";

export const SELECT_COLUMN_WIDTH = 40;

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
