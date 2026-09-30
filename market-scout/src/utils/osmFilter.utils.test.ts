import { describe, expect, it } from "vitest";

import {
    formatOsmFilter,
    formatPatterns,
    parseOsmFilterText,
    parsePatternsText,
} from "./osmFilter.utils";
import { slugify } from "./slug.utils";

describe("parseOsmFilterText", () => {
    it("treats empty text as no filter", () => {
        expect(parseOsmFilterText("")).toEqual({ ok: true, filter: null });
        expect(parseOsmFilterText("  \n \n")).toEqual({ ok: true, filter: null });
    });

    it("reads one alternative per line with AND-joined conditions", () => {
        const result = parseOsmFilterText("shop=electrical AND name~solar|inverter\nname~solar");
        expect(result).toEqual({
            ok: true,
            filter: { clauses: [["shop=electrical", "name~solar|inverter"], ["name~solar"]] },
        });
    });

    it("accepts AND in any case and extra spacing", () => {
        const result = parseOsmFilterText("  shop=hardware   and   name~pump  ");
        expect(result).toEqual({ ok: true, filter: { clauses: [["shop=hardware", "name~pump"]] } });
    });

    it("round-trips through formatOsmFilter", () => {
        const text = "shop=electrical AND name~solar|inverter\nname~battery";
        const parsed = parseOsmFilterText(text);
        expect(parsed.ok && formatOsmFilter(parsed.filter)).toBe(text);
        expect(formatOsmFilter(null)).toBe("");
    });

    it.each([
        ['no operator here', /should look like/],
        ["=value", /should look like/],
        ['name~solar"];out;//', /isn't allowed|character/],
        ["shop=hard;ware", /character/],
        ["name~a[b]", /character/],
        ["name~(unclosed", /valid pattern/],
    ])("rejects %s with a message naming the line", (line, message) => {
        const result = parseOsmFilterText(`shop=electrical\n${line}`);
        expect(result.ok).toBe(false);
        if (!result.ok) {
            expect(result.error).toMatch(/^Line 2:/);
            expect(result.error).toMatch(message);
        }
    });

    it("enforces the same size limits as the server", () => {
        const tooManyLines = Array.from({ length: 11 }, () => "a=1").join("\n");
        expect(parseOsmFilterText(tooManyLines)).toMatchObject({ ok: false });
        const tooManyConditions = Array.from({ length: 6 }, () => "a=1").join(" AND ");
        expect(parseOsmFilterText(tooManyConditions)).toMatchObject({ ok: false });
    });

    it("allows Urdu letters in values", () => {
        expect(parseOsmFilterText("name~سولر").ok).toBe(true);
    });
});

describe("parsePatternsText", () => {
    it("reads one pattern per line and ignores blanks", () => {
        expect(parsePatternsText("\\bdealer\n\n  authori[sz]ed ")).toEqual({
            ok: true,
            patterns: ["\\bdealer", "authori[sz]ed"],
        });
        expect(formatPatterns(["a", "b"])).toBe("a\nb");
        expect(formatPatterns(undefined)).toBe("");
    });

    it("reports an invalid pattern with its line number", () => {
        const result = parsePatternsText("fine\n(unclosed");
        expect(result).toMatchObject({ ok: false });
        if (!result.ok) expect(result.error).toMatch(/^Line 2:/);
    });

    it("limits length and count", () => {
        expect(parsePatternsText("x".repeat(101))).toMatchObject({ ok: false });
        expect(parsePatternsText(Array.from({ length: 51 }, () => "x").join("\n"))).toMatchObject({ ok: false });
    });
});

describe("slugify", () => {
    it("matches the backend's rule", () => {
        expect(slugify("Solar Dealer")).toBe("solar-dealer");
        expect(slugify("  Wholesale & Distribution! ")).toBe("wholesale-distribution");
        expect(slugify("سولر", "segment")).toBe("segment");
    });
});
