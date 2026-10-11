import { describe, expect, it } from "vitest";

import type { TProfileDetail } from "@/api/services/profiles/profiles.response.types";
import {
    emptyProfile,
    profileSchema,
    toFormValues,
    toRequestBody,
    type TProfileFormValues,
} from "./profileForm";

const detail: TProfileDetail = {
    id: 7,
    name: "Solar",
    slug: "solar",
    description: null,
    ideal_customer: null,
    is_active: true,
    segment_count: 2,
    term_count: 2,
    created_at: "2026-09-30T10:00:00",
    updated_at: null,
    scoring_config: {
        has_phone: 30, has_whatsapp_likely: 20, has_website: 10, has_email: 10, has_reviews: 10, name_matches_segment: 20,
    },
    segments: [
        { id: 1, name: "Dealer", slug: "dealer", description: "Sells", match_rules: { name_patterns: ["\\bdealer"] }, sort_order: 1 },
        { id: 2, name: "Installer", slug: "installer", description: null, match_rules: { name_patterns: [] }, sort_order: 2 },
    ],
    search_terms: [
        { id: 10, text: "solar dealer", segment_id: 1, segment_slug: "dealer", language: "en", is_active: true,
          osm_filter: { clauses: [["shop=electrical", "name~solar"], ["name~solar"]] } },
        { id: 11, text: "solar ki dukan", segment_id: 1, segment_slug: "dealer", language: "ur-roman", is_active: false, osm_filter: null },
    ],
};

const valid = (overrides: Partial<TProfileFormValues> = {}): TProfileFormValues => ({
    ...toFormValues(detail),
    ...overrides,
});

const issues = (values: TProfileFormValues) => {
    const result = profileSchema.safeParse(values);
    return result.success ? [] : result.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`);
};

describe("toFormValues / toRequestBody", () => {
    it("round-trips an existing profile, keeping ids and slugs so the server updates in place", () => {
        const body = toRequestBody(toFormValues(detail));

        expect(body.name).toBe("Solar");
        expect(body.description).toBeNull();
        expect(body.segments.map((s) => [s.id, s.slug, s.sort_order])).toEqual([[1, "dealer", 1], [2, "installer", 2]]);
        expect(body.segments[0].match_rules).toEqual({ name_patterns: ["\\bdealer"] });
        expect(body.search_terms.map((t) => [t.id, t.segment_slug, t.is_active])).toEqual([
            [10, "dealer", true],
            [11, "dealer", false],
        ]);
        expect(body.search_terms[0].osm_filter).toEqual({ clauses: [["shop=electrical", "name~solar"], ["name~solar"]] });
        expect(body.search_terms[1].osm_filter).toBeNull();
    });

    it("carries the ideal customer text both ways, trimmed, and clears it when blank", () => {
        const withText = toFormValues({ ...detail, ideal_customer: "Small HVAC shops" });

        expect(withText.idealCustomer).toBe("Small HVAC shops");
        expect(toFormValues(detail).idealCustomer).toBe("");
        expect(toRequestBody({ ...withText, idealCustomer: "  Small HVAC shops  " }).ideal_customer).toBe("Small HVAC shops");
        expect(toRequestBody({ ...withText, idealCustomer: "   " }).ideal_customer).toBeNull();
    });

    it("gives a new segment a slug from its name, and points its terms at it", () => {
        const values = valid({
            segments: [{ key: "k1", slug: "", name: "Wholesale & Distribution", description: "", patterns: "" }],
            terms: [{ text: "wholesaler", segmentKey: "k1", language: "en", isActive: true, osm: "" }],
        });

        const body = toRequestBody(values);

        expect(body.segments[0]).toMatchObject({ slug: "wholesale-distribution", id: undefined });
        expect(body.search_terms[0].segment_slug).toBe("wholesale-distribution");
    });

    it("a segment keeps its slug when renamed, so leads classified to it aren't orphaned", () => {
        const values = toFormValues(detail);
        values.segments[0].name = "Authorised Dealer";
        expect(toRequestBody(values).segments[0]).toMatchObject({ id: 1, slug: "dealer", name: "Authorised Dealer" });
    });
});

describe("profileSchema", () => {
    it("allows an ideal customer text up to the limit and not beyond", () => {
        expect(issues(valid({ idealCustomer: "x".repeat(2000) }))).toEqual([]);
        expect(issues(valid({ idealCustomer: "x".repeat(2001) }))).toEqual(["idealCustomer: At most 2000 characters"]);
    });

    it("accepts a complete profile and an empty new one with a name", () => {
        expect(issues(valid())).toEqual([]);
        expect(issues({ ...emptyProfile(), name: "Water pumps" })).toEqual([]);
    });

    it("needs a name of at least two characters", () => {
        expect(issues({ ...emptyProfile(), name: "A" })).toContain("name: At least 2 characters");
    });

    it("rejects two segments that would get the same slug", () => {
        const values = valid({
            segments: [
                { key: "a", slug: "", name: "Dealer", description: "", patterns: "" },
                { key: "b", slug: "", name: "dealer!", description: "", patterns: "" },
            ],
            terms: [],
        });
        expect(issues(values)).toContain("segments.1.name: Another segment already has this name");
    });

    it("rejects a term pointing at a segment that doesn't exist", () => {
        const values = valid({ terms: [{ text: "orphan", segmentKey: "gone", language: "en", isActive: true, osm: "" }] });
        expect(issues(values)).toContain("terms.0.segmentKey: Choose a segment");
    });

    it("rejects the same term twice in one segment, but allows it in another language", () => {
        const term = { text: "Solar Dealer", segmentKey: toFormValues(detail).segments[0].key, language: "en" as const, isActive: true, osm: "" };
        const base = toFormValues(detail);
        const segmentKey = base.segments[0].key;
        const withTerms = (terms: TProfileFormValues["terms"]) => ({ ...base, terms });

        expect(issues(withTerms([{ ...term, segmentKey }, { ...term, segmentKey, text: "solar dealer" }])))
            .toContain("terms.1.text: This search term is already in that segment");
        expect(issues(withTerms([{ ...term, segmentKey }, { ...term, segmentKey, language: "ur-roman" }]))).toEqual([]);
    });

    it("reports a bad OSM filter and a bad name pattern on the field that has it", () => {
        const base = toFormValues(detail);
        base.terms[0].osm = 'name~solar"];out;//';
        base.segments[0].patterns = "(unclosed";
        const found = issues(base);
        expect(found.some((line) => line.startsWith("terms.0.osm: Line 1:"))).toBe(true);
        expect(found.some((line) => line.startsWith("segments.0.patterns: Line 1:"))).toBe(true);
    });

    it("keeps scoring weights to whole numbers from 0 to 100", () => {
        const values = valid();
        values.scoring = { ...values.scoring, has_phone: 101, has_email: -1, has_website: 2.5 };
        const found = issues(values);
        expect(found).toEqual(
            expect.arrayContaining(["scoring.has_phone: 0 to 100", "scoring.has_email: 0 to 100", "scoring.has_website: A whole number"]),
        );
    });
});
