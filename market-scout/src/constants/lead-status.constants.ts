export const LEAD_STATUS = {
    NEW: "new",
    CONTACTED: "contacted",
    INTERESTED: "interested",
    MEETING: "meeting",
    QUOTED: "quoted",
    CUSTOMER: "customer",
    NOT_INTERESTED: "not_interested",
} as const;

export type LeadStatus = (typeof LEAD_STATUS)[keyof typeof LEAD_STATUS];

export const LEAD_STATUS_OPTIONS: ReadonlyArray<{
    value: LeadStatus;
    label: string;
    className: string;
}> = [
    { value: "new", label: "New", className: "bg-info text-info-foreground" },
    {
        value: "contacted",
        label: "Contacted",
        className: "bg-warning text-warning-foreground",
    },
    {
        value: "interested",
        label: "Interested",
        className: "bg-accent text-accent-foreground",
    },
    {
        value: "meeting",
        label: "Meeting",
        className: "bg-primary text-primary-foreground",
    },
    {
        value: "quoted",
        label: "Quoted",
        className: "bg-secondary text-secondary-foreground",
    },
    {
        value: "customer",
        label: "Customer",
        className: "bg-success text-success-foreground",
    },
    {
        value: "not_interested",
        label: "Not interested",
        className: "bg-muted text-muted-foreground",
    },
];

export const getLeadStatus = (value: string) =>
    LEAD_STATUS_OPTIONS.find((option) => option.value === value);
