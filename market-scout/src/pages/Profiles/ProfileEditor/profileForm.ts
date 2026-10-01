import { z } from "zod";

import type { TProfileBody } from "@/api/services/profiles/profiles.request.types";
import type {
    TProfileDetail,
    TScoringConfig,
} from "@/api/services/profiles/profiles.response.types";
import {
    formatOsmFilter,
    formatPatterns,
    parseOsmFilterText,
    parsePatternsText,
} from "@/utils/osmFilter.utils";
import { slugify } from "@/utils/slug.utils";

export const DEFAULT_SCORING: TScoringConfig = {
    has_phone: 30,
    has_whatsapp_likely: 20,
    has_website: 10,
    has_email: 10,
    has_reviews: 10,
    name_matches_segment: 20,
};

export const SCORING_FIELDS: ReadonlyArray<{
    name: keyof TScoringConfig;
    label: string;
    help: string;
}> = [
    { name: "has_phone", label: "Has a phone number", help: "Any phone or WhatsApp number" },
    { name: "has_whatsapp_likely", label: "Can be reached on WhatsApp", help: "A mobile number, which is almost always on WhatsApp" },
    { name: "has_website", label: "Has a website", help: "Its own site, not a social page" },
    { name: "has_email", label: "Has an email address", help: "Found on the listing or its website" },
    { name: "has_reviews", label: "Has reviews", help: "Three or more, a sign it is a real, active business" },
    { name: "name_matches_segment", label: "Name fits its segment", help: "e.g. \"Wholesale\" in a wholesaler's name" },
];

export type TSegmentValues = {
    key: string;
    id?: number;
    slug: string;
    name: string;
    description: string;
    patterns: string;
};

export type TTermValues = {
    id?: number;
    text: string;
    segmentKey: string;
    language: "en" | "ur-roman";
    isActive: boolean;
    osm: string;
};

export type TProfileFormValues = {
    name: string;
    description: string;
    isActive: boolean;
    scoring: TScoringConfig;
    segments: TSegmentValues[];
    terms: TTermValues[];
};

export const newKey = (): string => crypto.randomUUID();

const weight = z
    .number({ error: "0 to 100" })
    .int("A whole number")
    .min(0, "0 to 100")
    .max(100, "0 to 100");

const segmentSlug = (segment: { slug: string; name: string }) =>
    segment.slug || slugify(segment.name, "segment");

const segmentSchema = z
    .object({
        key: z.string(),
        id: z.number().optional(),
        slug: z.string(),
        name: z.string().trim().min(2, "At least 2 characters").max(100, "At most 100 characters"),
        description: z.string().max(500, "At most 500 characters"),
        patterns: z.string(),
    })
    .superRefine((segment, ctx) => {
        const parsed = parsePatternsText(segment.patterns);
        if (!parsed.ok) ctx.addIssue({ code: "custom", path: ["patterns"], message: parsed.error });
    });

const termSchema = z
    .object({
        id: z.number().optional(),
        text: z.string().trim().min(2, "At least 2 characters").max(150, "At most 150 characters"),
        segmentKey: z.string().min(1, "Choose a segment"),
        language: z.enum(["en", "ur-roman"]),
        isActive: z.boolean(),
        osm: z.string(),
    })
    .superRefine((term, ctx) => {
        const parsed = parseOsmFilterText(term.osm);
        if (!parsed.ok) ctx.addIssue({ code: "custom", path: ["osm"], message: parsed.error });
    });

export const profileSchema = z
    .object({
        name: z.string().trim().min(2, "At least 2 characters").max(100, "At most 100 characters"),
        description: z.string().max(500, "At most 500 characters"),
        isActive: z.boolean(),
        scoring: z.object({
            has_phone: weight,
            has_whatsapp_likely: weight,
            has_website: weight,
            has_email: weight,
            has_reviews: weight,
            name_matches_segment: weight,
        }),
        segments: z.array(segmentSchema).max(30, "At most 30 segments"),
        terms: z.array(termSchema).max(300, "At most 300 search terms"),
    })
    .superRefine((profile, ctx) => {
        const seenSlugs = new Map<string, number>();
        profile.segments.forEach((segment, index) => {
            const slug = segmentSlug(segment);
            if (seenSlugs.has(slug)) {
                ctx.addIssue({
                    code: "custom",
                    path: ["segments", index, "name"],
                    message: "Another segment already has this name",
                });
            }
            seenSlugs.set(slug, index);
        });

        const segmentKeys = new Set(profile.segments.map((segment) => segment.key));
        const seenTerms = new Set<string>();
        profile.terms.forEach((term, index) => {
            if (!segmentKeys.has(term.segmentKey)) {
                ctx.addIssue({ code: "custom", path: ["terms", index, "segmentKey"], message: "Choose a segment" });
            }
            const identity = `${term.segmentKey}|${term.text.trim().toLowerCase()}|${term.language}`;
            if (seenTerms.has(identity)) {
                ctx.addIssue({
                    code: "custom",
                    path: ["terms", index, "text"],
                    message: "This search term is already in that segment",
                });
            }
            seenTerms.add(identity);
        });
    });

export const emptyProfile = (): TProfileFormValues => ({
    name: "",
    description: "",
    isActive: true,
    scoring: { ...DEFAULT_SCORING },
    segments: [],
    terms: [],
});

export const toFormValues = (profile: TProfileDetail): TProfileFormValues => {
    const keyBySlug = new Map<string, string>();

    const segments = profile.segments.map((segment) => {
        const key = newKey();
        keyBySlug.set(segment.slug, key);
        return {
            key,
            id: segment.id,
            slug: segment.slug,
            name: segment.name,
            description: segment.description ?? "",
            patterns: formatPatterns(segment.match_rules?.name_patterns),
        };
    });

    return {
        name: profile.name,
        description: profile.description ?? "",
        isActive: profile.is_active,
        scoring: { ...DEFAULT_SCORING, ...profile.scoring_config },
        segments,
        terms: profile.search_terms.map((term) => ({
            id: term.id,
            text: term.text,
            segmentKey: keyBySlug.get(term.segment_slug) ?? "",
            language: term.language,
            isActive: term.is_active,
            osm: formatOsmFilter(term.osm_filter),
        })),
    };
};

export const toRequestBody = (values: TProfileFormValues): TProfileBody => {
    const slugByKey = new Map(values.segments.map((segment) => [segment.key, segmentSlug(segment)]));

    return {
        name: values.name.trim(),
        description: values.description.trim() || null,
        is_active: values.isActive,
        scoring_config: values.scoring,
        segments: values.segments.map((segment, index) => {
            const patterns = parsePatternsText(segment.patterns);
            return {
                id: segment.id,
                name: segment.name.trim(),
                slug: segmentSlug(segment),
                description: segment.description.trim() || null,
                match_rules: { name_patterns: patterns.ok ? patterns.patterns : [] },
                sort_order: index + 1,
            };
        }),
        search_terms: values.terms.map((term) => {
            const filter = parseOsmFilterText(term.osm);
            return {
                id: term.id,
                text: term.text.trim(),
                segment_slug: slugByKey.get(term.segmentKey) ?? "",
                osm_filter: filter.ok ? filter.filter : null,
                language: term.language,
                is_active: term.isActive,
            };
        }),
    };
};
