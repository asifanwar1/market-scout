export const ENDPOINTS = {
    AUTH: {
        CHANGE_PASSWORD: "/auth/change-password",
        LOGIN: "/auth/login",
        LOGOUT_ALL: "/auth/logout-all",
        ME: "/auth/me",
        REFRESH: "/auth/refresh",
    },
    BUSINESSES: {
        ASSIGNEES: "/businesses/assignees",
        BULK_UPDATE: "/businesses/bulk-update",
        ROOT: "/businesses/",
        detail: (id?: number | string) => `/businesses/${id}`,
        doNotContact: (id?: number | string) => `/businesses/${id}/do-not-contact`,
    },
    COMPLIANCE: {
        DO_NOT_CONTACT: "/compliance/do-not-contact",
    },
    EXPORTS: {
        LEADS_CSV: "/exports/leads.csv",
    },
    GEOGRAPHIES: {
        ROOT: "/geographies/",
        TREE: "/geographies/tree",
        detail: (id?: number | string) => `/geographies/${id}`,
    },
    IMPORTS: {
        PREVIEW: "/imports/preview",
        ROOT: "/imports/",
        cancel: (id?: number | string) => `/imports/${id}/cancel`,
        detail: (id?: number | string) => `/imports/${id}`,
    },
    INSIGHTS: {
        COVERAGE: "/insights/coverage",
        GAPS: "/insights/gaps",
        MOVERS: "/insights/movers",
        OVERVIEW: "/insights/overview",
        SOURCES: "/insights/sources",
        TIMELINE: "/insights/timeline",
    },
    PROFILES: {
        ROOT: "/profiles/",
        detail: (id?: number | string) => `/profiles/${id}`,
    },
    RUNS: {
        ESTIMATE: "/runs/estimate",
        ROOT: "/runs/",
        cancel: (id?: number | string) => `/runs/${id}/cancel`,
        detail: (id?: number | string) => `/runs/${id}`,
        resume: (id?: number | string) => `/runs/${id}/resume`,
        tasks: (id?: number | string) => `/runs/${id}/tasks`,
    },
    SHEETS: {
        ROOT: "/sheets/",
        SYNC: "/sheets/sync",
        TEST: "/sheets/test",
    },
    SOURCES: {
        ROOT: "/sources/",
        detail: (id?: number | string) => `/sources/${id}`,
        test: (id?: number | string) => `/sources/${id}/test`,
    },
    USERS: {
        ROOT: "/users/",
        detail: (id?: number | string) => `/users/${id}`,
    },
} as const;
