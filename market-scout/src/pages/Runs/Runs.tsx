import { Plus, Radar } from "lucide-react";
import { Link } from "react-router-dom";

import DataTable from "@/components/custom/DataTable";
import EmptyState from "@/components/custom/EmptyState";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ALL_OPTION_VALUE } from "@/constants";
import { RUN_STATUS_OPTIONS } from "@/constants/run-status.constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { runColumns } from "./Runs.columns";
import { RUNS_EMPTY_DESCRIPTION, RUNS_PAGE_DESCRIPTION, RUNS_PAGE_TITLE } from "./Runs.constants";
import { useRunsPage } from "./Runs.Container";

const Runs = () => {
    const {
        runs,
        total,
        hasRuns,
        hasStatusFilter,
        statusValue,
        page,
        pageSize,
        emptyTitle,
        isPending,
        getRunRowId,
        openRun,
        onStatusChange,
        onPageChange,
        onPageSizeChange,
    } = useRunsPage();

    const renderStatusOption = (option: (typeof RUN_STATUS_OPTIONS)[number]) => (
        <SelectItem key={option.value} value={option.value}>
            {option.label}
        </SelectItem>
    );

    const startRunAction = hasStatusFilter ? undefined : (
        <Button asChild>
            <Link to={APP_ROUTES.RUNS_NEW}>Start a run</Link>
        </Button>
    );

    return (
        <div className="space-y-4">
            <PageHeader
                title={RUNS_PAGE_TITLE}
                description={RUNS_PAGE_DESCRIPTION}
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
                <Select value={statusValue} onValueChange={onStatusChange}>
                    <SelectTrigger className="w-44" aria-label="Filter by status">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL_OPTION_VALUE}>All statuses</SelectItem>
                        {RUN_STATUS_OPTIONS.map(renderStatusOption)}
                    </SelectContent>
                </Select>
            </div>

            <DataTable
                columns={runColumns}
                data={runs}
                getRowId={getRunRowId}
                isLoading={isPending}
                onRowClick={openRun}
                emptyState={<EmptyState icon={Radar} title={emptyTitle} description={RUNS_EMPTY_DESCRIPTION} action={startRunAction} />}
            />

            {hasRuns && (
                <Pagination page={page} pageSize={pageSize} total={total} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />
            )}
        </div>
    );
};

export default Runs;
