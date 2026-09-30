import {
    flexRender,
    getCoreRowModel,
    useReactTable,
    type ColumnDef,
    type OnChangeFn,
    type RowSelectionState,
    type SortingState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import type { ReactNode } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

type TDataTableProps<T> = {
    columns: ColumnDef<T, unknown>[];
    data: T[];
    getRowId: (row: T) => string;
    isLoading?: boolean;
    // Sorting happens on the server, so the table only reports what was clicked.
    sorting?: SortingState;
    onSortingChange?: OnChangeFn<SortingState>;
    rowSelection?: RowSelectionState;
    onRowSelectionChange?: OnChangeFn<RowSelectionState>;
    onRowClick?: (row: T) => void;
    emptyState?: ReactNode;
    skeletonRows?: number;
};

const DataTable = <T,>({
    columns,
    data,
    getRowId,
    isLoading = false,
    sorting = [],
    onSortingChange,
    rowSelection = {},
    onRowSelectionChange,
    onRowClick,
    emptyState,
    skeletonRows = 8,
}: TDataTableProps<T>) => {
    // TanStack Table returns fresh function objects every render; the React Compiler would
    // memoise around them and the table would stop updating.
    "use no memo";

    // The lint warning below is the compiler noting the same thing the directive above handles.
    // eslint-disable-next-line react-hooks/incompatible-library
    const table = useReactTable({
        data,
        columns,
        getRowId,
        getCoreRowModel: getCoreRowModel(),
        manualSorting: true,
        enableSortingRemoval: false,
        state: { sorting, rowSelection },
        onSortingChange,
        onRowSelectionChange,
        enableRowSelection: !!onRowSelectionChange,
    });

    const isEmpty = !isLoading && data.length === 0;

    return (
        <div className="overflow-hidden rounded-lg border bg-card">
            <Table>
                <TableHeader className="bg-muted/40">
                    {table.getHeaderGroups().map((headerGroup) => (
                        <TableRow key={headerGroup.id} className="hover:bg-transparent">
                            {headerGroup.headers.map((header) => {
                                const canSort = header.column.getCanSort();
                                const sorted = header.column.getIsSorted();
                                return (
                                    <TableHead
                                        key={header.id}
                                        style={{ width: header.column.columnDef.size }}
                                        aria-sort={
                                            sorted === "asc"
                                                ? "ascending"
                                                : sorted === "desc"
                                                  ? "descending"
                                                  : undefined
                                        }
                                    >
                                        {header.isPlaceholder ? null : canSort ? (
                                            <button
                                                type="button"
                                                onClick={header.column.getToggleSortingHandler()}
                                                className="-ml-1 inline-flex items-center gap-1 rounded px-1 py-0.5 font-medium hover:bg-muted"
                                            >
                                                {flexRender(header.column.columnDef.header, header.getContext())}
                                                {sorted === "asc" ? (
                                                    <ArrowUp className="size-3.5" />
                                                ) : sorted === "desc" ? (
                                                    <ArrowDown className="size-3.5" />
                                                ) : (
                                                    <ChevronsUpDown className="size-3.5 text-muted-foreground/60" />
                                                )}
                                            </button>
                                        ) : (
                                            flexRender(header.column.columnDef.header, header.getContext())
                                        )}
                                    </TableHead>
                                );
                            })}
                        </TableRow>
                    ))}
                </TableHeader>
                <TableBody>
                    {isLoading &&
                        Array.from({ length: skeletonRows }).map((_, rowIndex) => (
                            <TableRow key={`skeleton-${rowIndex}`} className="hover:bg-transparent">
                                {columns.map((_column, columnIndex) => (
                                    <TableCell key={columnIndex}>
                                        <Skeleton className="h-5 w-full max-w-40" />
                                    </TableCell>
                                ))}
                            </TableRow>
                        ))}

                    {!isLoading &&
                        table.getRowModel().rows.map((row) => (
                            <TableRow
                                key={row.id}
                                data-state={row.getIsSelected() ? "selected" : undefined}
                                onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                                className={cn(onRowClick && "cursor-pointer")}
                            >
                                {row.getVisibleCells().map((cell) => (
                                    <TableCell key={cell.id}>
                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                    </TableCell>
                                ))}
                            </TableRow>
                        ))}

                    {isEmpty && (
                        <TableRow className="hover:bg-transparent">
                            <TableCell colSpan={columns.length} className="p-0">
                                {emptyState}
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </div>
    );
};

export default DataTable;
