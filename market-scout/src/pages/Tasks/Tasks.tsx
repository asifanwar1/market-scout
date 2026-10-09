import { CalendarCheck } from "lucide-react";

import type { TTask } from "@/api/services/pipeline/pipeline.response.types";
import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import TaskRow from "./Components/TaskRow";
import { MINE_LABEL, TASKS_PAGE_DESCRIPTION, TASKS_PAGE_TITLE } from "./Tasks.constants";
import { useTasksPage } from "./Tasks.Container";

const Tasks = () => {
    const {
        tasks,
        total,
        hasTasks,
        scope,
        scopeOptions,
        mine,
        page,
        pageSize,
        today,
        isPending,
        isUpdating,
        emptyTitle,
        emptyDescription,
        overdueCount,
        dueTodayCount,
        onScopeChange,
        onMineChange,
        onPageChange,
        onPageSizeChange,
        toggleDone,
    } = useTasksPage();

    const renderScope = (option: (typeof scopeOptions)[number]) => (
        <Button
            key={option.value}
            size="sm"
            variant={scope === option.value ? "default" : "outline"}
            aria-pressed={scope === option.value}
            onClick={() => onScopeChange(option.value)}
        >
            {option.label}
        </Button>
    );

    const renderTask = (task: TTask) => (
        <TaskRow key={task.id} task={task} today={today} isBusy={isUpdating} onToggle={toggleDone} />
    );

    return (
        <div className="space-y-4">
            <PageHeader title={TASKS_PAGE_TITLE} description={TASKS_PAGE_DESCRIPTION} />

            <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">{scopeOptions.map(renderScope)}</div>
                <div className="flex items-center gap-4">
                    {(overdueCount > 0 || dueTodayCount > 0) && (
                        <div className="flex items-center gap-2 text-sm">
                            {overdueCount > 0 && <Badge variant="destructive">{overdueCount} overdue</Badge>}
                            {dueTodayCount > 0 && <Badge variant="secondary">{dueTodayCount} due today</Badge>}
                        </div>
                    )}
                    <div className="flex items-center gap-2">
                        <Switch id="tasks-mine" checked={mine} onCheckedChange={onMineChange} />
                        <Label htmlFor="tasks-mine" className="text-sm font-normal">
                            {MINE_LABEL}
                        </Label>
                    </div>
                </div>
            </div>

            <Card className="p-0">
                {isPending ? (
                    <Loading />
                ) : hasTasks ? (
                    <ul className="divide-y">{tasks.map(renderTask)}</ul>
                ) : (
                    <EmptyState icon={CalendarCheck} title={emptyTitle} description={emptyDescription} />
                )}
            </Card>

            {hasTasks && (
                <Pagination page={page} pageSize={pageSize} total={total} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />
            )}
        </div>
    );
};

export default Tasks;
