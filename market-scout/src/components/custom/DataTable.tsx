import {
    flexRender,
    getCoreRowModel,
    useReactTable,
    type ColumnDef,
    type HeaderGroup,
    type OnChangeFn,
    type Row,
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
import { DEFAULT_SKELETON_ROWS } from "@/constants/limits.constants";

type THeaderGroup<T> = HeaderGroup<T>;
type THeader<T> = HeaderGroup<T>["headers"][number];
type TRow<T> = Row<T>;
type TCell<T> = ReturnType<Row<T>["getVisibleCells"]>[number];

const SORTED_ASC = "asc";
const SORTED_DESC = "desc";

const ARIA_SORT = {
    [SORTED_ASC]: "ascending",
    [SORTED_DESC]: "descending",
} as const;

type TDataTableProps<T> = {
    columns: ColumnDef<T>[];
    data: T[];
    getRowId: (row: T) => string;
    isLoading?: boolean;
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
    skeletonRows = DEFAULT_SKELETON_ROWS,
}: TDataTableProps<T>) => {
    "use no memo";

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
    const showSkeleton = isLoading;
    const showRows = !isLoading;
    const skeletonRowIndexes = Array.from({ length: skeletonRows }, (_, index) => index);

    const renderHeader = (header: THeader<T>) => {
        const canSort = header.column.getCanSort();
        const sorted = header.column.getIsSorted();
        const sortLabel = sorted ? ARIA_SORT[sorted] : undefined;
        const headerContent = flexRender(header.column.columnDef.header, header.getContext());

        const renderSortIcon = () => {
            if (sorted === SORTED_ASC) return <ArrowUp className="size-3.5" />;
            if (sorted === SORTED_DESC) return <ArrowDown className="size-3.5" />;
            return <ChevronsUpDown className="size-3.5 text-muted-foreground/60" />;
        };

        const renderHeaderContent = () => {
            if (header.isPlaceholder) return null;
            if (!canSort) return headerContent;
            return (
                <button
                    type="button"
                    onClick={header.column.getToggleSortingHandler()}
                    className="-ml-1 inline-flex items-center gap-1 rounded px-1 py-0.5 font-medium hover:bg-muted"
                >
                    {headerContent}
                    {renderSortIcon()}
                </button>
            );
        };

        return (
            <TableHead key={header.id} style={{ width: header.column.columnDef.size }} aria-sort={sortLabel}>
                {renderHeaderContent()}
            </TableHead>
        );
    };

    const renderHeaderGroup = (headerGroup: THeaderGroup<T>) => (
        <TableRow key={headerGroup.id} className="hover:bg-transparent">
            {headerGroup.headers.map(renderHeader)}
        </TableRow>
    );

    const renderSkeletonCell = (columnIndex: number) => (
        <TableCell key={columnIndex}>
            <Skeleton className="h-5 w-full max-w-40" />
        </TableCell>
    );

    const renderSkeletonRow = (rowIndex: number) => (
        <TableRow key={`skeleton-${rowIndex}`} className="hover:bg-transparent">
            {columns.map((_column, columnIndex) => renderSkeletonCell(columnIndex))}
        </TableRow>
    );

    const renderCell = (cell: TCell<T>) => (
        <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
    );

    const renderRow = (row: TRow<T>) => {
        const onClick = onRowClick ? () => onRowClick(row.original) : undefined;

        return (
            <TableRow
                key={row.id}
                data-state={row.getIsSelected() ? "selected" : undefined}
                onClick={onClick}
                className={cn(onRowClick && "cursor-pointer")}
            >
                {row.getVisibleCells().map(renderCell)}
            </TableRow>
        );
    };

    return (
        <div className="overflow-hidden rounded-lg border bg-card">
            <Table>
                <TableHeader className="bg-muted/40">{table.getHeaderGroups().map(renderHeaderGroup)}</TableHeader>
                <TableBody>
                    {showSkeleton && skeletonRowIndexes.map(renderSkeletonRow)}

                    {showRows && table.getRowModel().rows.map(renderRow)}

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
