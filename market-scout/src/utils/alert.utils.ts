import type { TAlertSettingsBody } from "@/api/services/alerts/alerts.request.types";
import type { TAlertSettings } from "@/api/services/alerts/alerts.response.types";
import { ALERT_SETTING_LIMITS } from "@/constants/alert.constants";

export type TAlertSettingsForm = {
    newLeadEnabled: boolean;
    newLeadMinScore: string;
    growingEnabled: boolean;
    growingMinNewReviews: string;
    growingMinPercent: string;
    reachableEnabled: boolean;
    maxPerRun: string;
};

export const toSettingsForm = (settings: TAlertSettings): TAlertSettingsForm => ({
    newLeadEnabled: settings.new_lead_enabled,
    newLeadMinScore: String(settings.new_lead_min_score),
    growingEnabled: settings.growing_enabled,
    growingMinNewReviews: String(settings.growing_min_new_reviews),
    growingMinPercent: String(settings.growing_min_percent),
    reachableEnabled: settings.reachable_enabled,
    maxPerRun: String(settings.max_per_run),
});

export const parseWholeNumber = (text: string, limits: { min: number; max: number }): number | null => {
    const trimmed = text.trim();
    if (!/^\d+$/.test(trimmed)) return null;
    const value = Number(trimmed);
    return value >= limits.min && value <= limits.max ? value : null;
};

export const toSettingsBody = (form: TAlertSettingsForm): TAlertSettingsBody | null => {
    const minScore = parseWholeNumber(form.newLeadMinScore, ALERT_SETTING_LIMITS.SCORE);
    const newReviews = parseWholeNumber(form.growingMinNewReviews, ALERT_SETTING_LIMITS.NEW_REVIEWS);
    const percent = parseWholeNumber(form.growingMinPercent, ALERT_SETTING_LIMITS.PERCENT);
    const perRun = parseWholeNumber(form.maxPerRun, ALERT_SETTING_LIMITS.PER_RUN);
    if (minScore === null || newReviews === null || percent === null || perRun === null) return null;
    return {
        new_lead_enabled: form.newLeadEnabled,
        new_lead_min_score: minScore,
        growing_enabled: form.growingEnabled,
        growing_min_new_reviews: newReviews,
        growing_min_percent: percent,
        reachable_enabled: form.reachableEnabled,
        max_per_run: perRun,
    };
};
