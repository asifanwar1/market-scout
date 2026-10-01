import type { LeadStatus } from "@/constants/lead-status.constants";
import type { EMPTY_KIND } from "./Leads.constants";

export type TEmptyKind = (typeof EMPTY_KIND)[keyof typeof EMPTY_KIND];

export type TBulkChange = {
    lead_status?: LeadStatus;
    assigned_to_id?: number | null;
};
