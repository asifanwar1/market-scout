import type { TGeographyNode } from "@/api/services/geographies/geographies.response.types";

export type TLocationDialogState =
    | { kind: "province"; node: null; parent: TGeographyNode }
    | { kind: "province"; node: TGeographyNode; parent: null }
    | { kind: "city"; node: null; parent: TGeographyNode }
    | { kind: "city"; node: TGeographyNode; parent: null };

export type TLocationFormValues = {
    name: string;
    latitude?: number;
    longitude?: number;
    radius_km?: number;
};
