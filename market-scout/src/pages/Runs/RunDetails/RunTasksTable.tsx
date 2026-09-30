import type { ColumnDef } from "@tanstack/react-table";

import type { TRunTask } from "@/api/services/runs/runs.response.types";
import DataTable from "@/components/custom/DataTable";
import Pagination from "@/components/custom/Pagination";
import StatusBadge from "@/components/custom/StatusBadge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { TASK_STATUS_OPTIONS } from "@/constants/run-status.constants";
import { getSourceLabel } from "@/utils/format.utils";

const ALL = "all";

const columns: ColumnDef<TRunTask, unknown>[] = [
    {
        id: "search",
        header: "Search",
        enableSorting: false,
        cell: ({ row }) => (
            <div className="min-w-0 max-w-64">
                <p className="truncate font-medium">{row.original.term_text}</p>
                <p className="text-xs text-muted-foreground">
                    {row.original.geography_name} · {row.original.segment_slug}
                </p>
            </div>
        ),
    },
    {
        id: "source",
        header: "Source",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{getSourceLabel(row.original.source_key)}</span>,
    },
    {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => {
            const status = TASK_STATUS_OPTIONS[row.original.status];
            return <StatusBadge label={status?.label ?? row.original.status} className={status?.className} />;
        },
    },
    {
        id: "found",
        header: "Found",
        enableSorting: false,
        cell: ({ row }) => (
            <span className="tabular-nums">
                {row.original.status === "done" ? row.original.results_count : "—"}
            </span>
        ),
    },
    {
        id: "new",
        header: "New",
        enableSorting: false,
        cell: ({ row }) => (
            <span className="tabular-nums">{row.original.status === "done" ? row.original.new_count : "—"}</span>
        ),
    },
    {
        id: "note",
        header: "Note",
        enableSorting: false,
        cell: ({ row }) => (
            <span className="block max-w-72 truncate text-sm text-muted-foreground" title={row.original.error ?? ""}>
                {row.original.error ?? ""}
            </span>
        ),
    },
];

type TRunTasksTableProps = {
    tasks: TRunTask[];
    total: number;
    isLoading: boolean;
    page: number;
    pageSize: number;
    status: string | null;
    onStatusChange: (status: string | null) => void;
    onPageChange: (page: number) => void;
};

const RunTasksTable = ({
    tasks,
    total,
    isLoading,
    page,
    pageSize,
    status,
    onStatusChange,
    onPageChange,
}: TRunTasksTableProps) => {
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
                <h2 className="text-lg font-semibold">Searches</h2>
                <Select
                    value={status ?? ALL}
                    onValueChange={(value) => onStatusChange(value === ALL ? null : value)}
                >
                    <SelectTrigger size="sm" className="w-40" aria-label="Filter searches by status">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL}>All searches</SelectItem>
                        {Object.entries(TASK_STATUS_OPTIONS).map(([value, option]) => (
                            <SelectItem key={value} value={value}>
                                {option.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
            <DataTable
                columns={columns}
                data={tasks}
                getRowId={(task) => String(task.id)}
                isLoading={isLoading}
                skeletonRows={5}
                emptyState={<p className="p-6 text-center text-sm text-muted-foreground">No searches to show.</p>}
            />
            {total > pageSize && (
                <Pagination page={page} pageSize={pageSize} total={total} onPageChange={onPageChange} />
            )}
        </div>
    );
};

export default RunTasksTable;
