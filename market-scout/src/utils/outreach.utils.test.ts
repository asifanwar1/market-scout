import { describe, expect, it } from "vitest";

import type { TContactPoint } from "@/api/services/businesses/businesses.response.types";
import type { TMessageTemplate, TPlaceholder } from "@/api/services/outreach/outreach.response.types";
import { TEMPLATE_CHANNEL } from "@/constants/outreach.constants";
import {
    appendPlaceholder,
    contactsForChannel,
    describePlaceholder,
    placeholderToken,
    previewText,
    supportsSubject,
    templatesForChannel,
} from "./outreach.utils";

const template = (id: number, channel: TMessageTemplate["channel"]): TMessageTemplate => ({
    id,
    name: `Template ${id}`,
    channel,
    subject: null,
    body: "Hello",
    created_at: "2026-10-01T00:00:00Z",
    updated_at: null,
});

describe("placeholderToken", () => {
    it("wraps the key in braces", () => {
        expect(placeholderToken("city")).toBe("{city}");
    });
});

describe("appendPlaceholder", () => {
    it("adds the placeholder straight into an empty message", () => {
        expect(appendPlaceholder("", "city")).toBe("{city}");
    });

    it("puts a space between words and the placeholder", () => {
        expect(appendPlaceholder("Hello", "business_name")).toBe("Hello {business_name}");
    });

    it("does not double a space or a line break", () => {
        expect(appendPlaceholder("Hello ", "city")).toBe("Hello {city}");
        expect(appendPlaceholder("Hello\n", "city")).toBe("Hello\n{city}");
    });
});

describe("describePlaceholder", () => {
    it("mentions the fallback when there is one", () => {
        const placeholder: TPlaceholder = { key: "contact_name", label: "Contact person", fallback: "there" };

        expect(describePlaceholder(placeholder)).toBe('Contact person (says "there" if unknown)');
    });

    it("is just the label when there is none", () => {
        expect(describePlaceholder({ key: "business_name", label: "Business name", fallback: null })).toBe("Business name");
    });
});

describe("templatesForChannel", () => {
    it("keeps templates for the channel and for any channel", () => {
        const all = [template(1, TEMPLATE_CHANNEL.WHATSAPP), template(2, TEMPLATE_CHANNEL.EMAIL), template(3, TEMPLATE_CHANNEL.ANY)];

        expect(templatesForChannel(all, "email").map((item) => item.id)).toEqual([2, 3]);
        expect(templatesForChannel(all, "whatsapp").map((item) => item.id)).toEqual([1, 3]);
    });
});

describe("supportsSubject", () => {
    it("is false only for WhatsApp templates", () => {
        expect(supportsSubject(TEMPLATE_CHANNEL.WHATSAPP)).toBe(false);
        expect(supportsSubject(TEMPLATE_CHANNEL.EMAIL)).toBe(true);
        expect(supportsSubject(TEMPLATE_CHANNEL.ANY)).toBe(true);
    });
});

describe("previewText", () => {
    it("flattens line breaks", () => {
        expect(previewText("Line one\n\nLine   two")).toBe("Line one Line two");
    });

    it("shortens long text with an ellipsis", () => {
        const result = previewText("a".repeat(200));

        expect(result.endsWith("…")).toBe(true);
        expect(result.length).toBe(91);
    });
});

const contact = (id: number, overrides: Partial<TContactPoint>): TContactPoint => ({
    id,
    kind: "phone",
    value: `+92300000000${id}`,
    is_mobile: false,
    whatsapp_likely: false,
    source_key: "osm",
    created_at: null,
    check_status: null,
    check_note: null,
    checked_at: null,
    ...overrides,
});

describe("contactsForChannel", () => {
    const contacts = [
        contact(1, { is_mobile: false }),
        contact(2, { is_mobile: true }),
        contact(3, { is_mobile: true, whatsapp_likely: true }),
        contact(4, { kind: "whatsapp" }),
        contact(5, { kind: "email", value: "a@noor.pk" }),
        contact(6, { kind: "email", value: "b@noor.pk", check_status: "bad" }),
        contact(7, { kind: "email", value: "c@noor.pk", check_status: "ok" }),
        contact(8, { kind: "facebook", value: "https://facebook.com/noor" }),
    ];

    it("offers phone and WhatsApp numbers for WhatsApp, best first", () => {
        expect(contactsForChannel(contacts, "whatsapp").map((item) => item.id)).toEqual([4, 3, 2, 1]);
    });

    it("offers only email addresses for email, leaving out ones that cannot receive mail", () => {
        expect(contactsForChannel(contacts, "email").map((item) => item.id)).toEqual([5, 7]);
    });

    it("is empty when the lead has nothing suitable", () => {
        expect(contactsForChannel([contact(8, { kind: "facebook" })], "whatsapp")).toEqual([]);
    });
});
