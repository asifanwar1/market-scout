export type TGeographyLevel = "country" | "province" | "city";

export type TGeographyNode = {
    id: number;
    name: string;
    slug: string;
    level: TGeographyLevel;
    latitude: number | null;
    longitude: number | null;
    radius_km: number | null;
    children: TGeographyNode[];
};

export type TGeographyTreeResponse = TGeographyNode[];
