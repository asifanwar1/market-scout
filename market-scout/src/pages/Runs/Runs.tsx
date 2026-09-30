import type { ColumnDef } from "@tanstack/react-table";
import { Plus, Radar } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import type { TRun } from "@/api/services/runs/runs.response.types";
import DataTable from "@/components/custom/DataTable";
import EmptyState from "@/components/custom/EmptyState";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import StatusBadge from "@/components/custom/StatusBadge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { RUN_STATUS_OPTIONS, getRunStatus } from "@/constants/run-status.constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatDateTime, formatUsd, getSourceLabel, pluralize } from "@/utils/format.utils";
import { useRunsPage } from "./Runs.Container";

const ALL = "all";

const sumStat = (run: TRun, field: string) =>
    Object.entries(run.stats)
        .filter(([source]) => source !== "website_enrichment")
        .reduce((total, [, stats]) => total + (stats[field] ?? 0), 0);

const columns: ColumnDef<TRun, unknown>[] = [
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
        size: 220,
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
        cell: ({ row }) => (
            <span className="text-sm">{row.original.source_keys.map(getSourceLabel).join(", ")}</span>
        ),
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
            <span className="whitespace-nowrap text-sm text-muted-foreground">
                {formatDateTime(row.original.started_at ?? row.original.created_at)}
            </span>
        ),
    },
];

const Runs = () => {
    const navigate = useNavigate();
    const { state, runs, total, isLoading, setStatus, setPage, setPageSize } = useRunsPage();

    return (
        <div className="space-y-4">
            <PageHeader
                title="Runs"
                description="Each run searches the chosen cities and adds new businesses to Leads."
                actions={
                    <Button asChild>
                        <Link to={APP_ROUTES.RUNS_NEW}>
                            <Plus />
                            New run
                        </Link>
                    </Button>
                }
            />

            <div className="flex items-center gap-2">
                <Select
                    value={state.status ?? ALL}
                    onValueChange={(value) =>
                        setStatus(value === ALL ? null : (value as NonNullable<typeof state.status>))
                    }
                >
                    <SelectTrigger className="w-44" aria-label="Filter by status">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL}>All statuses</SelectItem>
                        {RUN_STATUS_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                                {option.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>

            <DataTable
                columns={columns}
                data={runs}
                getRowId={(run) => String(run.id)}
                isLoading={isLoading}
                onRowClick={(run) => navigate(APP_ROUTES.RUNS_DETAILS.replace(":id", String(run.id)))}
                emptyState={
                    <EmptyState
                        icon={Radar}
                        title={state.status ? "No runs with this status" : "No runs yet"}
                        description="Start a run to search for businesses in the cities you sell in."
                        action={
                            state.status ? undefined : (
                                <Button asChild>
                                    <Link to={APP_ROUTES.RUNS_NEW}>Start a run</Link>
                                </Button>
                            )
                        }
                    />
                }
            />

            {total > 0 && (
                <Pagination
                    page={state.page}
                    pageSize={state.size}
                    total={total}
                    onPageChange={setPage}
                    onPageSizeChange={setPageSize}
                />
            )}
        </div>
    );
};

export default Runs;
