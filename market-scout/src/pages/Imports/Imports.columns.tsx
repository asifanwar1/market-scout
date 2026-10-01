import type { ColumnDef } from "@tanstack/react-table";

import type { TImport } from "@/api/services/imports/imports.response.types";
import StatusBadge from "@/components/custom/StatusBadge";
import { Progress } from "@/components/ui/progress";
import { getImportStatus } from "@/constants/import-status.constants";
import { formatCount, formatDateTime, pluralize } from "@/utils/format.utils";
import { PROGRESS_COLUMN_WIDTH } from "./Imports.constants";

export const importColumns: ColumnDef<TImport>[] = [
    {
        id: "list",
        header: "List",
        enableSorting: false,
        cell: ({ row }) => (
            <div className="min-w-0">
                <p className="font-medium">{row.original.label}</p>
                <p className="truncate text-xs text-muted-foreground">{row.original.filename}</p>
            </div>
        ),
    },
    {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => {
            const status = getImportStatus(row.original.status);
            return <StatusBadge label={status?.label ?? row.original.status} className={status?.className} />;
        },
    },
    {
        id: "progress",
        header: "Progress",
        enableSorting: false,
        size: PROGRESS_COLUMN_WIDTH,
        cell: ({ row }) => (
            <div className="w-48 space-y-1">
                <Progress value={row.original.progress_percent} />
                <p className="text-xs text-muted-foreground tabular-nums">
                    {formatCount(row.original.rows_done)} of {pluralize(row.original.rows_to_import, "row", "rows")}
                </p>
            </div>
        ),
    },
    {
        id: "new",
        header: "New leads",
        enableSorting: false,
        cell: ({ row }) => <span className="tabular-nums">{formatCount(row.original.stats.new ?? 0)}</span>,
    },
    {
        id: "known",
        header: "Already known",
        enableSorting: false,
        cell: ({ row }) => <span className="tabular-nums">{formatCount(row.original.stats.merged ?? 0)}</span>,
    },
    {
        id: "profile",
        header: "Profile",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.profile_name}</span>,
    },
    {
        id: "created",
        header: "Added",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm whitespace-nowrap text-muted-foreground">{formatDateTime(row.original.created_at)}</span>,
    },
];
