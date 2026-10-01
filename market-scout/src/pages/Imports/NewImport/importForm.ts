import type { TColumnMapping } from "@/api/services/imports/imports.request.types";
import type { TImportPreview } from "@/api/services/imports/imports.response.types";
import { LIST_LABEL_MIN_LENGTH } from "@/constants/limits.constants";

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

export const importProblem = ({ mapping, label, profileId, requireContact, lookupContacts }: TFormState): string | null => {
    if (!mapping.name) return "Choose which column holds the business name.";
    if (Boolean(mapping.latitude) !== Boolean(mapping.longitude)) {
        return "Choose both a latitude and a longitude column, or neither.";
    }
    if (requireContact && !lookupContacts && mapping.phones.length === 0 && mapping.emails.length === 0 && !mapping.website) {
        return "Choose at least one phone, email or website column, or untick “Skip rows with no contact details”, or look the phones up in Overture Maps.";
    }
    if (label.trim().length < LIST_LABEL_MIN_LENGTH) return "Give the list a name.";
    if (profileId === undefined) return "Choose a profile.";
    return null;
};

export const toggleColumn = (columns: string[], column: string, on: boolean): string[] =>
    on ? (columns.includes(column) ? columns : [...columns, column]) : columns.filter((item) => item !== column);
