import { describe, expect, it } from "vitest";

import type { TSource } from "@/api/services/sources/sources.response.types";
import { getUnavailableReason } from "./sources.utils";

const source = (overrides: Partial<TSource>): TSource => ({
    key: "x",
    name: "X",
    description: "",
    kind: "discovery",
    requires_api_key: false,
    is_paid: false,
    is_enabled: true,
    has_key: false,
    key_hint: null,
    key_source: null,
    key_needs_reentry: false,
    requires_dataset: false,
    dataset_ready: true,
    dataset_note: null,
    is_available: false,
    ...overrides,
});

describe("getUnavailableReason", () => {
    it("says a source that was switched off is switched off", () => {
        expect(getUnavailableReason(source({ is_enabled: false }))).toMatch(/switched off/);
    });

    it("names the missing data or key before the switch, since flipping it would not help", () => {
        expect(getUnavailableReason(source({ is_enabled: false, requires_dataset: true, dataset_ready: false }))).toMatch(/downloaded/);
        expect(getUnavailableReason(source({ is_enabled: false, requires_api_key: true }))).toMatch(/API key/);
    });

    it("asks for a key when that is what is missing", () => {
        expect(getUnavailableReason(source({ requires_api_key: true }))).toMatch(/API key/);
    });

    it("asks for the download when the data is missing", () => {
        expect(getUnavailableReason(source({ requires_dataset: true, dataset_ready: false }))).toMatch(/downloaded/);
    });

    it("never claims a missing download for a source that does not need one", () => {
        expect(getUnavailableReason(source({ requires_dataset: false, dataset_ready: false }))).not.toMatch(/downloaded/);
    });
});
