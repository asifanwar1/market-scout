/** Same rule as the backend's slugify, so a slug computed here matches the one it would assign. */
export const slugify = (value: string, fallback = "item"): string => {
    const slug = value
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
    return slug || fallback;
};
