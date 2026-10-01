import type { TGeographyLevel } from "./geographies.response.types";

export type TCreateGeographyBody = {
    name: string;
    level: TGeographyLevel;
    parent_id: number | null;
    latitude?: number | null;
    longitude?: number | null;
    radius_km?: number | null;
};

export type TUpdateGeographyBody = {
    name?: string;
    latitude?: number | null;
    longitude?: number | null;
    radius_km?: number | null;
};
