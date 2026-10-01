import type { ColumnDef } from "@tanstack/react-table";

import type { UserModel } from "@/api/models/user.model";
import StatusBadge from "@/components/custom/StatusBadge";
import { formatDate } from "@/utils/format.utils";
import { ACTIVE_BADGE_CLASS, INACTIVE_BADGE_CLASS, ROLE_BADGE_CLASSES, ROLE_LABELS } from "./Users.constants";

export const userColumns: ColumnDef<UserModel>[] = [
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
        cell: ({ row }) => <StatusBadge label={ROLE_LABELS[row.original.role]} className={ROLE_BADGE_CLASSES[row.original.role]} />,
    },
    {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
            <StatusBadge
                label={row.original.is_active ? "Active" : "Inactive"}
                className={row.original.is_active ? ACTIVE_BADGE_CLASS : INACTIVE_BADGE_CLASS}
            />
        ),
    },
    {
        id: "created",
        header: "Created",
        enableSorting: false,
        cell: ({ row }) => <span className="whitespace-nowrap text-sm text-muted-foreground">{formatDate(row.original.created_at)}</span>,
    },
];
