import type { TColumnMapping } from "@/api/services/imports/imports.request.types";
import type { TImportPreview } from "@/api/services/imports/imports.response.types";

export const EMPTY_MAPPING: TColumnMapping = {
    name: "",
    phones: [],
    emails: [],
    website: null,
    address: null,
    city: null,
    latitude: null,
    longitude: null,
    category: null,
};

const single = (value: string | string[] | null | undefined): string | null =>
    typeof value === "string" && value ? value : null;

const list = (value: string | string[] | null | undefined): string[] => (Array.isArray(value) ? value : []);

/** The server's best guess at which column is which, as a complete mapping. */
export const mappingFromSuggestion = (suggestion: TImportPreview["suggested_mapping"]): TColumnMapping => ({
    name: single(suggestion.name) ?? "",
    phones: list(suggestion.phones),
    emails: list(suggestion.emails),
    website: single(suggestion.website),
    address: single(suggestion.address),
    city: single(suggestion.city),
    latitude: single(suggestion.latitude),
    longitude: single(suggestion.longitude),
    category: single(suggestion.category),
});

/** "aedb-certified-installers_c3.csv" -> "Aedb certified installers c3": a starting name the person can edit. */
export const defaultLabel = (filename: string): string => {
    const base = filename.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ").replace(/\s+/g, " ").trim();
    return base ? base.charAt(0).toUpperCase() + base.slice(1) : "";
};

type TFormState = {
    mapping: TColumnMapping;
    label: string;
    profileId: number | undefined;
    requireContact: boolean;
    lookupContacts: boolean;
};

/** What stops the import from starting, in plain words, or null when it is ready. */
export const importProblem = ({ mapping, label, profileId, requireContact, lookupContacts }: TFormState): string | null => {
    if (!mapping.name) return "Choose which column holds the business name.";
    if (Boolean(mapping.latitude) !== Boolean(mapping.longitude)) {
        return "Choose both a latitude and a longitude column, or neither.";
    }
    // With the lookup on, a list of names alone is fine: the phones are found in Overture Maps.
    if (requireContact && !lookupContacts && mapping.phones.length === 0 && mapping.emails.length === 0 && !mapping.website) {
        return "Choose at least one phone, email or website column, or untick “Skip rows with no contact details”, or look the phones up in Overture Maps.";
    }
    if (label.trim().length < 2) return "Give the list a name.";
    if (profileId === undefined) return "Choose a profile.";
    return null;
};

/** Toggle a column in or out of a multi-column field (phones, emails). */
export const toggleColumn = (columns: string[], column: string, on: boolean): string[] =>
    on ? (columns.includes(column) ? columns : [...columns, column]) : columns.filter((item) => item !== column);
