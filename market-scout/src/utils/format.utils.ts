import { format, formatDistanceToNowStrict } from "date-fns";

const COUNTRY_PREFIX = "+92";
const MOBILE_PREFIX = "3";
const MOBILE_NATIONAL_LENGTH = 10;
const MOBILE_PREFIX_LENGTH = 3;
const WHATSAPP_CHAT_URL = "https://wa.me/";
const TWO_DIGIT_AREA_CODES = new Set(["21", "42", "51", "91"]);

export const formatPhone = (e164: string): string => {
    if (!e164.startsWith(COUNTRY_PREFIX)) return e164;
    const national = e164.slice(COUNTRY_PREFIX.length);
    if (national.startsWith(MOBILE_PREFIX) && national.length === MOBILE_NATIONAL_LENGTH) {
        return `0${national.slice(0, MOBILE_PREFIX_LENGTH)} ${national.slice(MOBILE_PREFIX_LENGTH)}`;
    }
    const areaLength = TWO_DIGIT_AREA_CODES.has(national.slice(0, 2)) ? 2 : 3;
    return `0${national.slice(0, areaLength)} ${national.slice(areaLength)}`;
};

export const whatsappLink = (e164: string): string =>
    `${WHATSAPP_CHAT_URL}${e164.replace(/\D/g, "")}`;

const parseServerDate = (value: string): Date =>
    new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`);

export const formatDate = (value: string | null | undefined): string => {
    if (!value) return "—";
    return format(parseServerDate(value), "d MMM yyyy");
};

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

export const isImportSource = (key: string): boolean => key.startsWith(IMPORT_PREFIX);

export const getSourceLabel = (key: string): string =>
    SOURCE_LABELS[key] ?? (isImportSource(key) ? key.slice(IMPORT_PREFIX.length) : key);
