import { ALERT_KIND } from "@/constants/alert.constants";

export const ALERTS_PAGE_TITLE = "Alerts";

export const ALERTS_PAGE_DESCRIPTION =
    "Things worth a look that turned up when searches ran: new leads that score well, businesses that are growing, and leads that can finally be contacted.";

export const ALERTS_EMPTY_TITLE = "No alerts yet";

export const ALERTS_EMPTY_UNREAD_TITLE = "Nothing unread";

export const ALERTS_EMPTY_DESCRIPTION = "Alerts appear after a run finishes and finds something that matches the limits set below.";

export const ALERT_KIND_FILTER_VALUES = [ALERT_KIND.NEW_LEAD, ALERT_KIND.GROWING, ALERT_KIND.REACHABLE] as const;

export const SETTINGS_TITLE = "What counts as an alert";

export const SETTINGS_DESCRIPTION = "Applies to every profile. Changes take effect from the next run.";

export const OPEN_LEAD_LABEL = "Open lead";
