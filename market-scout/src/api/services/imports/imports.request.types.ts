/** Which column of the file is which field, by the column's header. */
export type TColumnMapping = {
    name: string;
    phones: string[];
    emails: string[];
    website: string | null;
    address: string | null;
    city: string | null;
    latitude: string | null;
    longitude: string | null;
    category: string | null;
};

export type TImportOptions = {
    label: string;
    profile_id: number;
    segment_slug: string | null;
    default_geography_id: number | null;
    require_contact: boolean;
    lookup_contacts: boolean;
    mapping: TColumnMapping;
};

export type TGetImportsParams = {
    page?: number;
    limit?: number;
};
