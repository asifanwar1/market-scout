export const SOURCE_KIND = {
    DISCOVERY: "discovery",
    ENRICHMENT: "enrichment",
    IMPORT: "import",
} as const;

export const ENRICHMENT_SOURCE_KEY = "website_enrichment";
export const OVERTURE_SOURCE_KEY = "overture";

export const CREDENTIALS_SOURCE = {
    SAVED: "saved",
    ENVIRONMENT: "environment",
} as const;

export const CONTACT_KIND = {
    PHONE: "phone",
    WHATSAPP: "whatsapp",
    EMAIL: "email",
    FACEBOOK: "facebook",
    INSTAGRAM: "instagram",
} as const;

export const GAP_REASON = {
    NEVER_SEARCHED: "never_searched",
    FEW_FOUND: "few_found",
} as const;

export const CANCELLED_ERROR_NAMES = ["CanceledError", "AbortError"];

export const AUTH_SCHEME_BEARER = "Bearer";
