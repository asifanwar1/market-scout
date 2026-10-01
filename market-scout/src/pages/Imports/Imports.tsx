import type { ColumnDef } from "@tanstack/react-table";
import { FileUp, Plus } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import type { TImport } from "@/api/services/imports/imports.response.types";
import DataTable from "@/components/custom/DataTable";
import EmptyState from "@/components/custom/EmptyState";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import StatusBadge from "@/components/custom/StatusBadge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { getImportStatus } from "@/constants/import-status.constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatCount, formatDateTime, pluralize } from "@/utils/format.utils";
import { useImportsPage } from "./Imports.Container";

const columns: ColumnDef<TImport, unknown>[] = [
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
        size: 220,
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
        cell: ({ row }) => (
            <span className="text-sm whitespace-nowrap text-muted-foreground">{formatDateTime(row.original.created_at)}</span>
        ),
    },
];

const Imports = () => {
    const navigate = useNavigate();
    const { state, imports, total, isLoading, setPage, setPageSize } = useImportsPage();

    return (
        <div className="space-y-4">
            <PageHeader
                title="Imports"
                description="Bring in lists you already have, such as certified installers, chamber directories or customs records. They go through the same matching, scoring and do-not-contact checks as a search."
                actions={
                    <Button asChild>
                        <Link to={APP_ROUTES.IMPORTS_NEW}>
                            <Plus />
                            New import
                        </Link>
                    </Button>
                }
            />

            <DataTable
                columns={columns}
                data={imports}
                getRowId={(item) => String(item.id)}
                isLoading={isLoading}
                onRowClick={(item) => navigate(APP_ROUTES.IMPORTS_DETAILS.replace(":id", String(item.id)))}
                emptyState={
                    <EmptyState
                        icon={FileUp}
                        title="No imports yet"
                        description="Upload a CSV or Excel file of businesses and they are added to Leads, matched against the ones you already have."
                        action={
                            <Button asChild>
                                <Link to={APP_ROUTES.IMPORTS_NEW}>Import a list</Link>
                            </Button>
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

export default Imports;
