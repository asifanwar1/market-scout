import { CalendarClock, Plus } from "lucide-react";
import { Link } from "react-router-dom";

import type { TSchedule } from "@/api/services/schedules/schedules.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import ScheduleRow from "./Components/ScheduleRow";
import WorkerStatus from "./Components/WorkerStatus";
import {
    DELETE_DESCRIPTION,
    DELETE_TITLE,
    NEW_REPEAT_LABEL,
    SCHEDULES_EMPTY_DESCRIPTION,
    SCHEDULES_EMPTY_TITLE,
    SCHEDULES_PAGE_DESCRIPTION,
    SCHEDULES_PAGE_TITLE,
} from "./Schedules.constants";
import { useSchedulesPage } from "./Schedules.Container";

const Schedules = () => {
    const {
        schedules,
        total,
        hasSchedules,
        page,
        pageSize,
        isPending,
        isBusy,
        isDeleting,
        isDeleteOpen,
        jobsStatus,
        newRepeatUrl,
        onPageChange,
        onPageSizeChange,
        toggleActive,
        runNow,
        requestDelete,
        closeDelete,
        confirmDelete,
    } = useSchedulesPage();

    const renderSchedule = (schedule: TSchedule) => (
        <ScheduleRow
            key={schedule.id}
            schedule={schedule}
            isBusy={isBusy}
            onToggle={toggleActive}
            onRunNow={runNow}
            onDelete={requestDelete}
        />
    );

    const newRepeatAction = (
        <Button asChild>
            <Link to={newRepeatUrl}>
                <Plus />
                {NEW_REPEAT_LABEL}
            </Link>
        </Button>
    );

    return (
        <div className="space-y-4">
            <PageHeader title={SCHEDULES_PAGE_TITLE} description={SCHEDULES_PAGE_DESCRIPTION} actions={newRepeatAction} />

            <WorkerStatus status={jobsStatus} />

            <Card className="p-0">
                {isPending ? (
                    <Loading />
                ) : hasSchedules ? (
                    <ul className="divide-y">{schedules.map(renderSchedule)}</ul>
                ) : (
                    <EmptyState
                        icon={CalendarClock}
                        title={SCHEDULES_EMPTY_TITLE}
                        description={SCHEDULES_EMPTY_DESCRIPTION}
                        action={newRepeatAction}
                    />
                )}
            </Card>

            {hasSchedules && (
                <Pagination page={page} pageSize={pageSize} total={total} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />
            )}

            <ConfirmationModal
                open={isDeleteOpen}
                title={DELETE_TITLE}
                description={DELETE_DESCRIPTION}
                confirmText="Delete"
                destructive
                isLoading={isDeleting}
                onConfirm={confirmDelete}
                onClose={closeDelete}
            />
        </div>
    );
};

export default Schedules;
