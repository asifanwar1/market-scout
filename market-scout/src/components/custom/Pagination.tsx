import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { formatCount } from "@/utils/format.utils";

const PAGE_SIZES = [10, 25, 50, 100];

type TPaginationProps = {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
    onPageSizeChange?: (pageSize: number) => void;
};

const Pagination = ({
    page,
    pageSize,
    total,
    onPageChange,
    onPageSizeChange,
}: TPaginationProps) => {
    const pageCount = Math.max(1, Math.ceil(total / pageSize));
    const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
    const last = Math.min(page * pageSize, total);

    const renderSize = (size: (typeof PAGE_SIZES)[number]) => (
        <SelectItem key={size} value={String(size)}>
            {size}
        </SelectItem>
    );
    return (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <p className="text-muted-foreground">
                {total === 0
                    ? "No results"
                    : `Showing ${formatCount(first)}–${formatCount(last)} of ${formatCount(total)}`}
            </p>
            <div className="flex items-center gap-4">
                {onPageSizeChange && (
                    <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Rows</span>
                        <Select
                            value={String(pageSize)}
                            onValueChange={(value) => onPageSizeChange(Number(value))}
                        >
                            <SelectTrigger size="sm" className="w-[4.5rem]">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {PAGE_SIZES.map(renderSize)}
                            </SelectContent>
                        </Select>
                    </div>
                )}
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="icon-sm"
                        aria-label="Previous page"
                        disabled={page <= 1}
                        onClick={() => onPageChange(page - 1)}
                    >
                        <ChevronLeft />
                    </Button>
                    <span className="min-w-20 text-center text-muted-foreground tabular-nums">
                        Page {page} of {pageCount}
                    </span>
                    <Button
                        variant="outline"
                        size="icon-sm"
                        aria-label="Next page"
                        disabled={page >= pageCount}
                        onClick={() => onPageChange(page + 1)}
                    >
                        <ChevronRight />
                    </Button>
                </div>
            </div>
        </div>
    );
};

export default Pagination;
