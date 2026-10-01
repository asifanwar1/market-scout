import { format, formatDistanceToNowStrict } from "date-fns";

// Two-digit area codes in Pakistan (Karachi 21, Lahore 42, Islamabad/Rawalpindi 51, Peshawar 91);
// the rest have three digits.
const TWO_DIGIT_AREA_CODES = new Set(["21", "42", "51", "91"]);

/** "+923004438424" -> "0300 4438424", "+924235771769" -> "042 35771769". Anything else is returned as is. */
export const formatPhone = (e164: string): string => {
    if (!e164.startsWith("+92")) return e164;
    const national = e164.slice(3);
    if (national.startsWith("3") && national.length === 10) {
        return `0${national.slice(0, 3)} ${national.slice(3)}`;
    }
    const areaLength = TWO_DIGIT_AREA_CODES.has(national.slice(0, 2)) ? 2 : 3;
    return `0${national.slice(0, areaLength)} ${national.slice(areaLength)}`;
};

export const whatsappLink = (e164: string): string =>
    `https://wa.me/${e164.replace(/\D/g, "")}`;

// The backend sends UTC timestamps without a zone suffix.
const parseServerDate = (value: string): Date =>
    new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`);

export const formatDate = (value: string | null | undefined): string => {
    if (!value) return "—";
    return format(parseServerDate(value), "d MMM yyyy");
};

/** "16 Aug": for tight spaces where the year is obvious. */
export const formatShortDate = (value: string | null | undefined): string => {
    if (!value) return "—";
    return format(parseServerDate(value), "d MMM");
};

export const formatDateTime = (value: string | null | undefined): string => {
    if (!value) return "—";
    return format(parseServerDate(value), "d MMM yyyy, h:mm a");
};

export const formatRelative = (value: string | null | undefined): string => {
    if (!value) return "—";
    return `${formatDistanceToNowStrict(parseServerDate(value))} ago`;
};

export const formatCount = (value: number): string =>
    new Intl.NumberFormat("en-US").format(value);

/** pluralize(1, "search", "searches") -> "1 search"; pluralize(3, ...) -> "3 searches". */
export const pluralize = (count: number, singular: string, plural: string): string =>
    `${formatCount(count)} ${count === 1 ? singular : plural}`;

export const formatUsd = (value: number): string =>
    new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 2,
    }).format(value);

export const SOURCE_LABELS: Record<string, string> = {
    osm: "OpenStreetMap",
    overture: "Overture Maps",
    google_places: "Google Places",
    website_enrichment: "Website",
};

const IMPORT_PREFIX = "import:";

/** A list brought in from a file is a source named after the list ("import:AEDB installers"). */
export const isImportSource = (key: string): boolean => key.startsWith(IMPORT_PREFIX);

export const getSourceLabel = (key: string): string =>
    SOURCE_LABELS[key] ?? (isImportSource(key) ? key.slice(IMPORT_PREFIX.length) : key);
