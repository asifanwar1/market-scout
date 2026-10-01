import type { TListResponse } from "@/api/types/common";
import type { TColumnMapping } from "./imports.request.types";

export type TImportPreview = {
    filename: string;
    columns: string[];
    row_count: number;
    sample: Record<string, string>[];
    suggested_mapping: Partial<Record<keyof TColumnMapping, string | string[] | null>>;
};

export type TImportStatus = "queued" | "running" | "cancelling" | "completed" | "failed" | "cancelled";

export type TImport = {
    id: number;
    label: string;
    source_key: string;
    filename: string;
    profile_id: number | null;
    profile_name: string;
    segment_slug: string | null;
    default_geography_id: number | null;
    default_geography_name: string | null;
    require_contact: boolean;
    lookup_contacts: boolean;
    status: TImportStatus;
    rows_total: number;
    rows_to_import: number;
    rows_done: number;
    progress_percent: number;
    // Why rows were set aside before importing, e.g. { no_name: 3, no_contact: 12 }.
    skipped: Record<string, number>;
    // found, new, merged, blocked, with_phone, with_website, with_email, errors, no_city, looked_up
    stats: Record<string, number>;
    error: string | null;
    created_by_id: number | null;
    created_at: string | null;
    started_at: string | null;
    finished_at: string | null;
};

export type TGetImportsResponse = TListResponse<TImport>;
