import type { ColumnDef } from "@tanstack/react-table";
import { Plus, Search, UserCog } from "lucide-react";
import { parseAsInteger, parseAsString, parseAsStringLiteral, useQueryStates } from "nuqs";
import { useEffect, useState } from "react";

import type { UserModel } from "@/api/models/user.model";
import DataTable from "@/components/custom/DataTable";
import EmptyState from "@/components/custom/EmptyState";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import StatusBadge from "@/components/custom/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { USER_ROLE } from "@/constants";
import { useGetUsers } from "@/hooks/api/users.queries";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { formatDate } from "@/utils/format.utils";
import UserDialog from "./UserDialog";

const ALL = "all";

const urlState = {
    q: parseAsString.withDefault(""),
    role: parseAsStringLiteral([USER_ROLE.ADMIN, USER_ROLE.SALES] as const),
    page: parseAsInteger.withDefault(1),
    size: parseAsInteger.withDefault(25),
};

const columns: ColumnDef<UserModel, unknown>[] = [
    {
        id: "user",
        header: "User",
        enableSorting: false,
        cell: ({ row }) => (
            <div className="min-w-0">
                <p className="truncate font-medium">{row.original.full_name}</p>
                <p className="truncate text-xs text-muted-foreground">{row.original.email}</p>
            </div>
        ),
    },
    {
        id: "role",
        header: "Role",
        enableSorting: false,
        cell: ({ row }) => (
            <StatusBadge
                label={row.original.role === USER_ROLE.ADMIN ? "Admin" : "Sales"}
                className={row.original.role === USER_ROLE.ADMIN ? "bg-accent text-accent-foreground" : "bg-secondary text-secondary-foreground"}
            />
        ),
    },
    {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
            <StatusBadge
                label={row.original.is_active ? "Active" : "Inactive"}
                className={row.original.is_active ? "bg-success text-success-foreground" : "bg-muted text-muted-foreground"}
            />
        ),
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

const Users = () => {
    const [state, setState] = useQueryStates(urlState, { history: "replace" });

    const [searchInput, setSearchInput] = useState(state.q);
    const debouncedSearch = useDebouncedValue(searchInput, 350);
    useEffect(() => {
        if (debouncedSearch !== state.q) void setState({ q: debouncedSearch || null, page: 1 });
        // eslint-disable-next-line react-hooks/exhaustive-deps -- only react to the debounced text
    }, [debouncedSearch]);

    const { data, isPending } = useGetUsers({
        search: state.q || undefined,
        role: state.role ?? undefined,
        page: state.page,
        limit: state.size,
    });
    const users = data?.data ?? [];
    const total = data?.count ?? 0;

    const [dialogOpen, setDialogOpen] = useState(false);
    const [editing, setEditing] = useState<UserModel | null>(null);

    const openCreate = () => {
        setEditing(null);
        setDialogOpen(true);
    };
    const openEdit = (user: UserModel) => {
        setEditing(user);
        setDialogOpen(true);
    };

    return (
        <div className="space-y-4">
            <PageHeader
                title="Users"
                description="The people who can sign in. Sales accounts work the leads; admins also run searches and manage settings."
                actions={
                    <Button onClick={openCreate}>
                        <Plus />
                        New user
                    </Button>
                }
            />

            <div className="flex flex-wrap items-center gap-2">
                <div className="relative min-w-56 max-w-xs flex-1">
                    <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        value={searchInput}
                        onChange={(event) => setSearchInput(event.target.value)}
                        placeholder="Search name or email…"
                        aria-label="Search users"
                        className="pl-8"
                    />
                </div>
                <Select
                    value={state.role ?? ALL}
                    onValueChange={(value) =>
                        void setState({ role: value === ALL ? null : (value as typeof USER_ROLE.ADMIN | typeof USER_ROLE.SALES), page: 1 })
                    }
                >
                    <SelectTrigger className="w-40" aria-label="Filter by role">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL}>All roles</SelectItem>
                        <SelectItem value={USER_ROLE.ADMIN}>Admins</SelectItem>
                        <SelectItem value={USER_ROLE.SALES}>Sales</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            <DataTable
                columns={columns}
                data={users}
                getRowId={(user) => String(user.id)}
                isLoading={isPending}
                onRowClick={openEdit}
                emptyState={
                    <EmptyState
                        icon={UserCog}
                        title="No users match"
                        description="Try a different search or role."
                    />
                }
            />

            {total > 0 && (
                <Pagination
                    page={state.page}
                    pageSize={state.size}
                    total={total}
                    onPageChange={(page) => void setState({ page })}
                    onPageSizeChange={(size) => void setState({ size, page: 1 })}
                />
            )}

            <UserDialog open={dialogOpen} user={editing} onClose={() => setDialogOpen(false)} />
        </div>
    );
};

export default Users;
