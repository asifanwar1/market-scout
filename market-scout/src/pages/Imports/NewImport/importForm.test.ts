import { describe, expect, it } from "vitest";

import { EMPTY_MAPPING, defaultLabel, importProblem, mappingFromSuggestion, toggleColumn } from "./importForm";

describe("mappingFromSuggestion", () => {
    it("turns the server's guess into a complete mapping", () => {
        const mapping = mappingFromSuggestion({
            name: "Company",
            phones: ["Phone", "Mobile"],
            emails: ["Email"],
            website: null,
            city: "City",
        });

        expect(mapping).toEqual({
            ...EMPTY_MAPPING,
            name: "Company",
            phones: ["Phone", "Mobile"],
            emails: ["Email"],
            city: "City",
        });
    });

    it("copes with nothing being recognised", () => {
        expect(mappingFromSuggestion({})).toEqual(EMPTY_MAPPING);
    });
});

describe("defaultLabel", () => {
    it("makes a readable name out of the file name", () => {
        expect(defaultLabel("aedb-certified-installers_c3.csv")).toBe("Aedb certified installers c3");
        expect(defaultLabel("KCCI members 2026.xlsx")).toBe("KCCI members 2026");
    });

    it("handles odd names", () => {
        expect(defaultLabel("list")).toBe("List");
        expect(defaultLabel(".csv")).toBe("");
    });
});

describe("importProblem", () => {
    const ready = {
        mapping: { ...EMPTY_MAPPING, name: "Company", phones: ["Phone"] },
        label: "AEDB installers",
        profileId: 1,
        requireContact: true,
        lookupContacts: false,
    };

    it("is null when everything needed is there", () => {
        expect(importProblem(ready)).toBeNull();
    });

    it("needs a name column", () => {
        expect(importProblem({ ...ready, mapping: { ...ready.mapping, name: "" } })).toMatch(/business name/);
    });

    it("needs both coordinates or neither", () => {
        expect(importProblem({ ...ready, mapping: { ...ready.mapping, latitude: "Lat" } })).toMatch(/latitude and a longitude/);
        expect(importProblem({ ...ready, mapping: { ...ready.mapping, latitude: "Lat", longitude: "Lon" } })).toBeNull();
    });

    it("needs a way to contact the business unless rows without one are kept", () => {
        const noContact = { ...ready, mapping: { ...EMPTY_MAPPING, name: "Company" } };
        expect(importProblem(noContact)).toMatch(/phone, email or website/);
        expect(importProblem({ ...noContact, requireContact: false })).toBeNull();
        expect(importProblem({ ...noContact, mapping: { ...noContact.mapping, website: "Web" } })).toBeNull();
    });

    it("accepts a list of names alone when the phones are looked up", () => {
        const namesOnly = { ...ready, mapping: { ...EMPTY_MAPPING, name: "Company" } };
        expect(importProblem(namesOnly)).toMatch(/Overture/);
        expect(importProblem({ ...namesOnly, lookupContacts: true })).toBeNull();
    });

    it("needs a list name and a profile", () => {
        expect(importProblem({ ...ready, label: " x " })).toMatch(/name the list|Give the list a name/);
        expect(importProblem({ ...ready, profileId: undefined })).toMatch(/profile/);
    });
});

describe("toggleColumn", () => {
    it("adds a column once and removes it", () => {
        expect(toggleColumn(["Phone"], "Mobile", true)).toEqual(["Phone", "Mobile"]);
        expect(toggleColumn(["Phone", "Mobile"], "Mobile", true)).toEqual(["Phone", "Mobile"]);
        expect(toggleColumn(["Phone", "Mobile"], "Phone", false)).toEqual(["Mobile"]);
    });
});
