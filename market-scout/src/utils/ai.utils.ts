import type { TAiBatch } from "@/api/services/ai/ai.response.types";
import { AI_MODEL_LABELS } from "@/constants/ai.constants";
import { formatCount } from "./format.utils";
import { percentOf } from "./pipeline.utils";

const SMALL_AMOUNT_LIMIT = 1;
const SMALL_AMOUNT_DIGITS = 3;
const LARGE_AMOUNT_DIGITS = 2;
const UNKNOWN_MODEL = "an AI model";

export const formatAiCost = (value: number): string =>
    `$${value.toLocaleString("en-US", {
        minimumFractionDigits: value < SMALL_AMOUNT_LIMIT ? SMALL_AMOUNT_DIGITS : LARGE_AMOUNT_DIGITS,
        maximumFractionDigits: value < SMALL_AMOUNT_LIMIT ? SMALL_AMOUNT_DIGITS : LARGE_AMOUNT_DIGITS,
    })}`;

export const getAiModelLabel = (modelId: string | null): string =>
    modelId ? (AI_MODEL_LABELS[modelId] ?? modelId) : UNKNOWN_MODEL;

export const describeBatch = (batch: TAiBatch): string[] =>
    [
        [batch.analyzed, "analysed"],
        [batch.skipped, "skipped"],
        [batch.declined, "declined by the AI"],
        [batch.failed, "failed"],
    ]
        .filter(([count]) => (count as number) > 0)
        .map(([count, label]) => `${formatCount(count as number)} ${label}`);

export const batchProgress = (batch: TAiBatch): number => percentOf(batch.done, batch.total);
