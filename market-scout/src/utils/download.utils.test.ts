import { describe, expect, it } from "vitest";

import { GENERIC_ERROR_MESSAGE } from "@/constants/Validation-messages.constants";
import { getBlobErrorMessage, todayStamp } from "./download.utils";

const blobError = (body: string) => ({ response: { data: new Blob([body], { type: "application/json" }) } });

describe("getBlobErrorMessage", () => {
    it("reads the server's message out of a failed download", async () => {
        expect(await getBlobErrorMessage(blobError('{"detail":"Choose a profile to filter by segment"}'))).toBe(
            "Choose a profile to filter by segment",
        );
    });

    it("falls back to the generic message when the body isn't JSON or has no message", async () => {
        expect(await getBlobErrorMessage(blobError("<html>bad gateway</html>"))).toBe(GENERIC_ERROR_MESSAGE);
        expect(await getBlobErrorMessage(blobError('{"detail":[{"msg":"x"}]}'))).toBe(GENERIC_ERROR_MESSAGE);
    });

    it("handles an ordinary (non-blob) error response", async () => {
        expect(await getBlobErrorMessage({ response: { data: { detail: "Not found" } } })).toBe("Not found");
    });

    it("handles a failure with no response at all", async () => {
        expect(await getBlobErrorMessage(new Error("Network Error"))).toBe("Network Error");
    });
});

describe("todayStamp", () => {
    it("is a YYYY-MM-DD date", () => {
        expect(todayStamp()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });
});
