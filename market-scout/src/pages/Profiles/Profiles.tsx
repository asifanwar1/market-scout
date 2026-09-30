import type { ColumnDef } from "@tanstack/react-table";
import { Layers, Plus } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import type { TProfileListItem } from "@/api/services/profiles/profiles.response.types";
import DataTable from "@/components/custom/DataTable";
import EmptyState from "@/components/custom/EmptyState";
import PageHeader from "@/components/custom/PageHeader";
import StatusBadge from "@/components/custom/StatusBadge";
import { Button } from "@/components/ui/button";
import { useGetAllProfiles } from "@/hooks/api/profiles.queries";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatDate } from "@/utils/format.utils";

const columns: ColumnDef<TProfileListItem, unknown>[] = [
    {
        id: "name",
        header: "Profile",
        enableSorting: false,
        cell: ({ row }) => (
            <div className="min-w-0 max-w-96">
                <p className="truncate font-medium">{row.original.name}</p>
                {row.original.description && (
                    <p className="truncate text-xs text-muted-foreground">{row.original.description}</p>
                )}
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
                className={row.original.is_active ? "bg-success text-success-foreground" : "bg-muted text-muted-foreground"}
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
        cell: ({ row }) => (
            <span className="whitespace-nowrap text-sm text-muted-foreground">{formatDate(row.original.created_at)}</span>
        ),
    },
];

const Profiles = () => {
    const navigate = useNavigate();
    const { data, isPending } = useGetAllProfiles();

    return (
        <div className="space-y-4">
            <PageHeader
                title="Profiles"
                description="Each profile is an industry to look for: which kinds of business, and what to search for. Solar was the first; add others without touching any code."
                actions={
                    <Button asChild>
                        <Link to={APP_ROUTES.PROFILES_NEW}>
                            <Plus />
                            New profile
                        </Link>
                    </Button>
                }
            />

            <DataTable
                columns={columns}
                data={data?.data ?? []}
                getRowId={(profile) => String(profile.id)}
                isLoading={isPending}
                skeletonRows={4}
                onRowClick={(profile) => navigate(APP_ROUTES.PROFILES_DETAILS.replace(":id", String(profile.id)))}
                emptyState={
                    <EmptyState
                        icon={Layers}
                        title="No profiles yet"
                        description="Create one to describe what to look for, or run `python -m scripts.seed` on the server for the solar profile."
                    />
                }
            />
        </div>
    );
};

export default Profiles;
