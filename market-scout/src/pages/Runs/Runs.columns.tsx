import type { ColumnDef } from "@tanstack/react-table";

import type { TRun } from "@/api/services/runs/runs.response.types";
import StatusBadge from "@/components/custom/StatusBadge";
import { Progress } from "@/components/ui/progress";
import { getRunStatus } from "@/constants/run-status.constants";
import { formatDateTime, formatUsd, getSourceLabel, pluralize } from "@/utils/format.utils";
import { ENRICHMENT_SOURCE_KEY } from "@/constants/source.constants";
import { PROGRESS_COLUMN_WIDTH } from "./Runs.constants";

const sumStat = (run: TRun, field: string): number =>
    Object.entries(run.stats)
        .filter(([source]) => source !== ENRICHMENT_SOURCE_KEY)
        .reduce((total, [, stats]) => total + (stats[field] ?? 0), 0);

export const runColumns: ColumnDef<TRun>[] = [
    {
        id: "run",
        header: "Run",
        enableSorting: false,
        cell: ({ row }) => (
            <div className="min-w-0">
                <p className="font-medium">Run #{row.original.id}</p>
                <p className="truncate text-xs text-muted-foreground">{row.original.profile_name}</p>
            </div>
        ),
    },
    {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => {
            const status = getRunStatus(row.original.status);
            return <StatusBadge label={status?.label ?? row.original.status} className={status?.className} />;
        },
    },
    {
        id: "progress",
        header: "Progress",
        enableSorting: false,
        size: PROGRESS_COLUMN_WIDTH,
        cell: ({ row }) => {
            const { progress_percent, tasks_done, tasks_failed, tasks_skipped, tasks_total } = row.original;
            return (
                <div className="w-48 space-y-1">
                    <Progress value={progress_percent} />
                    <p className="text-xs text-muted-foreground tabular-nums">
                        {tasks_done + tasks_failed + tasks_skipped} of {pluralize(tasks_total, "search", "searches")}
                        {tasks_failed > 0 && ` · ${tasks_failed} failed`}
                    </p>
                </div>
            );
        },
    },
    {
        id: "sources",
        header: "Sources",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.source_keys.map(getSourceLabel).join(", ")}</span>,
    },
    {
        id: "new",
        header: "New leads",
        enableSorting: false,
        cell: ({ row }) => <span className="tabular-nums">{sumStat(row.original, "new")}</span>,
    },
    {
        id: "cost",
        header: "Cost",
        enableSorting: false,
        cell: ({ row }) =>
            row.original.paid_requests_used > 0 ? (
                <span className="tabular-nums" title={`${row.original.paid_requests_used} billable requests (estimate)`}>
                    {formatUsd(row.original.estimated_cost_usd)}
                </span>
            ) : (
                <span className="text-muted-foreground">Free</span>
            ),
    },
    {
        id: "created",
        header: "Started",
        enableSorting: false,
        cell: ({ row }) => (
            <span className="whitespace-nowrap text-sm text-muted-foreground">{formatDateTime(row.original.started_at ?? row.original.created_at)}</span>
        ),
    },
];
