import type { ColumnDef } from "@tanstack/react-table";
import { Globe, MessageCircle } from "lucide-react";

import type { TBusinessListItem } from "@/api/services/businesses/businesses.response.types";
import ScoreBadge from "@/components/custom/ScoreBadge";
import StatusBadge from "@/components/custom/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { getLeadStatus } from "@/constants";
import { formatPhone, formatRelative } from "@/utils/format.utils";

// Sortable columns carry an accessorFn (TanStack only offers sorting on those); their ids
// are the `sort` values the API understands.
export const leadColumns: ColumnDef<TBusinessListItem, unknown>[] = [
    {
        id: "select",
        size: 40,
        enableSorting: false,
        header: ({ table }) => (
            <Checkbox
                aria-label="Select all leads on this page"
                checked={
                    table.getIsAllPageRowsSelected() ||
                    (table.getIsSomePageRowsSelected() && "indeterminate")
                }
                onCheckedChange={(checked) => table.toggleAllPageRowsSelected(checked === true)}
            />
        ),
        cell: ({ row }) => (
            <Checkbox
                aria-label={`Select ${row.original.name}`}
                checked={row.getIsSelected()}
                onCheckedChange={(checked) => row.toggleSelected(checked === true)}
                // Ticking a row must not also open it.
                onClick={(event) => event.stopPropagation()}
            />
        ),
    },
    {
        id: "name",
        header: "Lead",
        accessorFn: (row) => row.name,
        cell: ({ row }) => (
            <div className="min-w-0 max-w-64">
                <p className="truncate font-medium">{row.original.name}</p>
                <p className="truncate text-xs text-muted-foreground">
                    {row.original.address ?? "No address"}
                </p>
            </div>
        ),
    },
    {
        id: "segment",
        header: "Segment",
        enableSorting: false,
        cell: ({ row }) =>
            row.original.segment_name ? (
                <Badge variant="outline">{row.original.segment_name}</Badge>
            ) : (
                <span className="text-muted-foreground">—</span>
            ),
    },
    {
        id: "score",
        header: "Score",
        accessorFn: (row) => row.score,
        cell: ({ row }) => <ScoreBadge score={row.original.score} />,
    },
    {
        id: "contact",
        header: "Contact",
        enableSorting: false,
        cell: ({ row }) => {
            const { primary_phone, whatsapp_likely, email, website } = row.original;
            if (!primary_phone && !email && !website) {
                return <span className="text-muted-foreground">No contact details yet</span>;
            }
            return (
                <div className="min-w-0 max-w-56 space-y-0.5 text-sm">
                    {primary_phone && (
                        <p className="flex items-center gap-1.5 tabular-nums">
                            {formatPhone(primary_phone)}
                            {whatsapp_likely && (
                                <MessageCircle
                                    className="size-3.5 text-success-foreground"
                                    aria-label="WhatsApp likely"
                                />
                            )}
                        </p>
                    )}
                    {email && <p className="truncate text-xs text-muted-foreground">{email}</p>}
                    {website && (
                        <p className="flex items-center gap-1 truncate text-xs text-muted-foreground">
                            <Globe className="size-3 shrink-0" />
                            <span className="truncate">{website.replace(/^https?:\/\//, "")}</span>
                        </p>
                    )}
                </div>
            );
        },
    },
    {
        id: "location",
        header: "Location",
        enableSorting: false,
        cell: ({ row }) => (
            <div className="text-sm">
                <p>{row.original.city ?? "—"}</p>
                <p className="text-xs text-muted-foreground">{row.original.province}</p>
            </div>
        ),
    },
    {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => {
            const status = getLeadStatus(row.original.lead_status);
            return <StatusBadge label={status?.label ?? row.original.lead_status} className={status?.className} />;
        },
    },
    {
        id: "assigned",
        header: "Assigned to",
        enableSorting: false,
        cell: ({ row }) =>
            row.original.assigned_to ? (
                <span className="text-sm">{row.original.assigned_to.full_name}</span>
            ) : (
                <span className="text-muted-foreground">Unassigned</span>
            ),
    },
    {
        id: "last_seen",
        header: "Last seen",
        accessorFn: (row) => row.last_seen_at,
        cell: ({ row }) => (
            <span className="whitespace-nowrap text-sm text-muted-foreground">
                {formatRelative(row.original.last_seen_at)}
            </span>
        ),
    },
];
