
export const NO_COLUMN_VALUE = "__none__";
export const NAME_FIELD = "name";

export type TSingleField = "name" | "website" | "address" | "city" | "latitude" | "longitude" | "category";

export type TSingleFieldConfig = { field: TSingleField; label: string; hint?: string; required?: boolean };

export const SINGLE_FIELDS: TSingleFieldConfig[] = [
    { field: "name", label: "Business name", required: true },
    { field: "website", label: "Website" },
    { field: "address", label: "Address", hint: "Also used to find the city when there is no city column" },
    { field: "city", label: "City" },
    { field: "latitude", label: "Latitude", hint: "Optional; places the business on the map" },
    { field: "longitude", label: "Longitude" },
    { field: "category", label: "Category or type", hint: "Optional; kept with the lead" },
];
