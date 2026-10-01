import type { TSource } from "@/api/services/sources/sources.response.types";

export const getUnavailableReason = (source: TSource): string => {
    if (source.requires_api_key && !source.has_key) return "Not available: it needs an API key (add one on the Sources screen).";
    if (source.requires_dataset && !source.dataset_ready) return "Not available: its data hasn't been downloaded yet (see the Sources screen).";
    if (!source.is_enabled) return "Not available: switched off on the Sources screen.";
    return "Not available.";
};
