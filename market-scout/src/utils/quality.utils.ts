import type { TScoringTrait } from "@/api/services/quality/quality.response.types";
import { CHECK_COUNT_LABELS } from "@/constants/quality.constants";
import { pluralize } from "@/utils/format.utils";

export const describeCheckCounts = (counts: Record<string, number>): string[] =>
    CHECK_COUNT_LABELS.filter(({ key }) => (counts[key] ?? 0) > 0).map(({ key, singular, plural }) => {
        const count = counts[key];
        return `${count} ${count === 1 ? singular : plural}`;
    });

export const describeTrait = (trait: TScoringTrait): string => {
    if (trait.difference === null) return `${pluralize(trait.with_count, "lead", "leads")} with, ${pluralize(trait.without_count, "lead", "leads")} without`;
    const direction = trait.difference >= 0 ? "more" : "less";
    return `Closes ${Math.abs(trait.difference)} points ${direction} often with it`;
};

export const weightChange = (trait: TScoringTrait): number => trait.suggested_weight - trait.current_weight;

export const formatRate = (rate: number | null): string => (rate === null ? "—" : `${rate}%`);
