export const INTEGRATIONS_PAGE_TITLE = "Integrations";

export const INTEGRATIONS_PAGE_DESCRIPTION =
    "Let your other software and automation tools read leads, add them, and hear about new ones. Keys and webhooks are for admins only.";

export const KEYS_TITLE = "API keys";

export const KEYS_DESCRIPTION =
    "A key lets another program use the public API without a login. Keys can read leads; an admin can also let a key add leads and change their status, notes and history. A key can never manage users, settings or other keys.";

export const KEYS_EMPTY = "No API keys yet.";

export const KEY_CREATED_TITLE = "Copy your new key now";

export const KEY_CREATED_DESCRIPTION = "This is the only time the full key is shown. If you lose it, revoke it and make a new one.";

export const KEY_REVOKE_TITLE = "Revoke this key?";

export const KEY_REVOKE_DESCRIPTION = "Anything using it stops working straight away. This cannot be undone.";

export const KEY_WRITE_LABEL = "Can add leads and change them";

export const KEY_WRITE_HELP = "Off means the key can only read. Turn it on only for software you trust.";

export const WEBHOOKS_TITLE = "Webhooks";

export const WEBHOOKS_DESCRIPTION =
    "Market Scout calls an address you give it when something happens, for example a new lead or a deal won. Each call is signed so your software can check it came from here.";

export const WEBHOOKS_EMPTY = "No webhooks yet.";

export const SECRET_CREATED_TITLE = "Copy the signing secret now";

export const SECRET_CREATED_DESCRIPTION =
    "Your software uses this secret to check that a call really came from Market Scout. It is shown only once; you can make a new one later from the webhook's row.";

export const WEBHOOK_DELETE_TITLE = "Delete this webhook?";

export const WEBHOOK_DELETE_DESCRIPTION = "Its delivery history is deleted too. Nothing more is sent to its address.";

export const WEBHOOK_ROTATE_TITLE = "Make a new signing secret?";

export const WEBHOOK_ROTATE_DESCRIPTION = "The old secret stops matching immediately. Update your software with the new one.";

export const WEBHOOK_URL_PLACEHOLDER = "https://example.com/hooks/market-scout";

export const WEBHOOK_URL_HELP = "Must be a public https:// address.";

export const WEBHOOK_URL_HELP_PRIVATE = "Local addresses and plain http:// are allowed on this server for testing.";

export const DELIVERIES_TITLE = "Recent deliveries";

export const DELIVERIES_EMPTY = "Nothing has been sent yet. Press Test on the webhook to send a sample.";

export const DELIVERIES_PAGE_SIZE = 8;

export const HELP_TITLE = "Using the API";

export const HELP_INTRO =
    "Send the key in an Authorization: Bearer header (or X-API-Key). The public API lives under /api/v1/public and is limited to 120 reads or 60 writes per minute for each key.";

export const HELP_ENDPOINTS: ReadonlyArray<{ method: string; path: string; note: string }> = [
    { method: "GET", path: "/leads", note: "List leads. Accepts the same filters as the Leads page, plus page and limit." },
    { method: "GET", path: "/leads/{id}", note: "One lead with contacts, score, AI result and deal outcome." },
    { method: "GET", path: "/leads/{id}/activities", note: "The lead's history." },
    { method: "POST", path: "/leads", note: "Add a lead (needs a write key). A business already in the list is merged, not duplicated." },
    { method: "PATCH", path: "/leads/{id}", note: "Change status, notes, contact person or deal outcome (needs a write key)." },
    { method: "POST", path: "/leads/{id}/activities", note: "Add a note or call to the history (needs a write key)." },
];

export const HELP_WEBHOOK_TITLE = "Checking a webhook call";

export const HELP_WEBHOOK_TEXT =
    "Each call is a JSON POST with the headers X-MarketScout-Event, X-MarketScout-Delivery and X-MarketScout-Signature (t=<seconds>,v1=<hex>). Compute HMAC-SHA256 of \"<t>.<raw body>\" with your signing secret and compare it with v1. A call that gets anything other than a 2xx answer is tried again up to 5 times, so your software should ignore a delivery id it has already handled.";

export const HELP_CURL = 'curl -H "Authorization: Bearer ms_your_key" "{base}/public/leads?min_score=70&limit=20"';
