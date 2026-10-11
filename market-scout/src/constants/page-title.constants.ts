import { APP_ROUTES } from "@/routes/appRoutes";

const STATIC_TITLES: Record<string, string> = {
    [APP_ROUTES.LEADS]: "Leads",
    [APP_ROUTES.TASKS]: "Tasks",
    [APP_ROUTES.ALERTS]: "Alerts",
    [APP_ROUTES.OUTREACH]: "Outreach",
    [APP_ROUTES.DO_NOT_CONTACT]: "Do not contact",
    [APP_ROUTES.RUNS]: "Runs",
    [APP_ROUTES.RUNS_NEW]: "New run",
    [APP_ROUTES.SCHEDULES]: "Repeating searches",
    [APP_ROUTES.QUALITY]: "Data quality",
    [APP_ROUTES.INTEGRATIONS]: "Integrations",
    [APP_ROUTES.PROFILES]: "Profiles",
    [APP_ROUTES.PROFILES_NEW]: "New profile",
    [APP_ROUTES.LOCATIONS]: "Locations",
    [APP_ROUTES.SOURCES]: "Sources",
    [APP_ROUTES.AI]: "AI assistant",
    [APP_ROUTES.USERS]: "Users",
};

export const getPageTitle = (pathname: string): string => {
    const clean = pathname.replace(/\/+$/, "") || "/";
    if (STATIC_TITLES[clean]) return STATIC_TITLES[clean];

    const runMatch = clean.match(/^\/runs\/(\d+)$/);
    if (runMatch) return `Run #${runMatch[1]}`;
    if (/^\/profiles\/\d+$/.test(clean)) return "Edit profile";

    return "Market Scout";
};
