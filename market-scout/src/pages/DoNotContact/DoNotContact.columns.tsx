import type { ColumnDef } from "@tanstack/react-table";
import { Undo2 } from "lucide-react";

import type { TDoNotContactResponse } from "@/api/services/businesses/businesses.response.types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate, formatPhone } from "@/utils/format.utils";
import {
    ACTIONS_COLUMN_WIDTH,
    DO_NOT_CONTACT_KIND,
    EMPTY_REASON_PLACEHOLDER,
    KIND_LABELS,
    PLUS_SIGN,
} from "./DoNotContact.constants";

const formatIdentifier = (identifier: string): string => (identifier.startsWith(PLUS_SIGN) ? formatPhone(identifier) : identifier);

export const getDoNotContactColumns = (
    isAdmin: boolean,
    onLift: (entry: TDoNotContactResponse) => void,
): ColumnDef<TDoNotContactResponse>[] => {
    const baseColumns: ColumnDef<TDoNotContactResponse>[] = [
        {
            id: "kind",
            header: "Type",
            enableSorting: false,
            cell: ({ row }) => <Badge variant="outline">{KIND_LABELS[row.original.kind]}</Badge>,
        },
        {
            id: "who",
            header: "Blocked",
            enableSorting: false,
            cell: ({ row }) => {
                const { kind, value, identifiers } = row.original;
                return (
                    <div className="min-w-0 max-w-80">
                        <p className="truncate font-medium">{kind === DO_NOT_CONTACT_KIND.PHONE ? formatPhone(value) : value}</p>
                        {identifiers.length > 0 && (
                            <p className="truncate text-xs text-muted-foreground">Also blocked: {identifiers.map(formatIdentifier).join(", ")}</p>
                        )}
                    </div>
                );
            },
        },
        {
            id: "reason",
            header: "Reason",
            enableSorting: false,
            cell: ({ row }) => <span className="text-sm text-muted-foreground">{row.original.reason ?? EMPTY_REASON_PLACEHOLDER}</span>,
        },
        {
            id: "added",
            header: "Added",
            enableSorting: false,
            cell: ({ row }) => <span className="whitespace-nowrap text-sm text-muted-foreground">{formatDate(row.original.created_at)}</span>,
        },
    ];

    if (!isAdmin) return baseColumns;

    const actionsColumn: ColumnDef<TDoNotContactResponse> = {
        id: "actions",
        header: "",
        enableSorting: false,
        size: ACTIONS_COLUMN_WIDTH,
        cell: ({ row }) => (
            <Button variant="ghost" size="sm" onClick={() => onLift(row.original)}>
                <Undo2 />
                Lift block
            </Button>
        ),
    };

    return [...baseColumns, actionsColumn];
};
