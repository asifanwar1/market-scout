import type { TOsmFilter } from "@/api/services/profiles/profiles.response.types";

const CONDITION = /^([A-Za-z0-9_:]+)(=|~)(.+)$/;
const SAFE_VALUE = /^[\p{L}\p{N}_\s|.\-&()+*?]+$/u;
const MAX_CLAUSES = 10;
const MAX_CONDITIONS = 5;
const AND = /\s+AND\s+/i;

export const OSM_FILTER_EXAMPLE = "shop=electrical AND name~solar|inverter";

export type TParsedFilter =
    | { ok: true; filter: TOsmFilter | null }
    | { ok: false; error: string };

export const parseOsmFilterText = (text: string): TParsedFilter => {
    const lines = text
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);

    if (lines.length === 0) return { ok: true, filter: null };
    if (lines.length > MAX_CLAUSES) {
        return { ok: false, error: `At most ${MAX_CLAUSES} alternatives (lines)` };
    }

    const clauses: string[][] = [];
    for (const [index, line] of lines.entries()) {
        const conditions = line.split(AND).map((condition) => condition.trim());
        if (conditions.length > MAX_CONDITIONS) {
            return { ok: false, error: `Line ${index + 1}: at most ${MAX_CONDITIONS} conditions joined with AND` };
        }
        for (const condition of conditions) {
            const error = validateCondition(condition);
            if (error) return { ok: false, error: `Line ${index + 1}: ${error}` };
        }
        clauses.push(conditions);
    }
    return { ok: true, filter: { clauses } };
};

const validateCondition = (condition: string): string | null => {
    const match = CONDITION.exec(condition);
    if (!match) return `"${condition}" should look like key=value or key~regex`;

    const [, , operator, value] = match;
    if (!SAFE_VALUE.test(value)) {
        return `"${condition}" contains a character that isn't allowed (quotes, brackets, semicolons)`;
    }
    if (operator === "~") {
        try {
            new RegExp(value);
        } catch {
            return `"${value}" isn't a valid pattern`;
        }
    }
    return null;
};

export const formatOsmFilter = (filter: TOsmFilter | null | undefined): string =>
    (filter?.clauses ?? []).map((clause) => clause.join(" AND ")).join("\n");

const MAX_PATTERNS = 50;
const MAX_PATTERN_LENGTH = 100;

export type TParsedPatterns = { ok: true; patterns: string[] } | { ok: false; error: string };

export const parsePatternsText = (text: string): TParsedPatterns => {
    const patterns = text
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);

    if (patterns.length > MAX_PATTERNS) {
        return { ok: false, error: `At most ${MAX_PATTERNS} patterns` };
    }
    for (const [index, pattern] of patterns.entries()) {
        if (pattern.length > MAX_PATTERN_LENGTH) {
            return { ok: false, error: `Line ${index + 1}: at most ${MAX_PATTERN_LENGTH} characters` };
        }
        try {
            new RegExp(pattern);
        } catch {
            return { ok: false, error: `Line ${index + 1}: "${pattern}" isn't a valid pattern` };
        }
    }
    return { ok: true, patterns };
};

export const formatPatterns = (patterns: string[] | undefined): string => (patterns ?? []).join("\n");
