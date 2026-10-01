import type { ColumnDef } from "@tanstack/react-table";

import type { TProfileListItem } from "@/api/services/profiles/profiles.response.types";
import StatusBadge from "@/components/custom/StatusBadge";
import { formatDate } from "@/utils/format.utils";
import { ACTIVE_BADGE_CLASS, INACTIVE_BADGE_CLASS } from "./Profiles.constants";

export const profileColumns: ColumnDef<TProfileListItem>[] = [
    {
        id: "name",
        header: "Profile",
        enableSorting: false,
        cell: ({ row }) => (
            <div className="min-w-0 max-w-96">
                <p className="truncate font-medium">{row.original.name}</p>
                {row.original.description && <p className="truncate text-xs text-muted-foreground">{row.original.description}</p>}
            </div>
        ),
    },
    {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
            <StatusBadge
                label={row.original.is_active ? "Active" : "Switched off"}
                className={row.original.is_active ? ACTIVE_BADGE_CLASS : INACTIVE_BADGE_CLASS}
            />
        ),
    },
    {
        id: "segments",
        header: "Segments",
        enableSorting: false,
        cell: ({ row }) => <span className="tabular-nums">{row.original.segment_count}</span>,
    },
    {
        id: "terms",
        header: "Search terms",
        enableSorting: false,
        cell: ({ row }) => <span className="tabular-nums">{row.original.term_count}</span>,
    },
    {
        id: "created",
        header: "Created",
        enableSorting: false,
        cell: ({ row }) => <span className="whitespace-nowrap text-sm text-muted-foreground">{formatDate(row.original.created_at)}</span>,
    },
];
