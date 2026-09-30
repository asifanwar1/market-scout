import { AlertTriangle, ArrowLeft, Ban, Loader2, Play, Users } from "lucide-react";
import { Link } from "react-router-dom";

import ConfirmationModal from "@/components/custom/ConfirmationModal";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import StatusBadge from "@/components/custom/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { getRunStatus } from "@/constants/run-status.constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatCount, formatDateTime, formatUsd, getSourceLabel } from "@/utils/format.utils";
import { useRunDetails } from "./RunDetails.Container";
import RunStatsTable from "./RunStatsTable";
import RunTasksTable from "./RunTasksTable";

const Stat = ({ label, value }: { label: string; value: string }) => (
    <div>
        <dt className="text-xs text-muted-foreground">{label}</dt>
        <dd className="text-lg font-semibold tabular-nums">{value}</dd>
    </div>
);

const RunDetails = () => {
    const {
        run,
        isLoading,
        isError,
        isActive,
        tasks,
        tasksTotal,
        isTasksLoading,
        taskPage,
        taskPageSize,
        taskStatus,
        setTaskStatus,
        setTaskPage,
        showCancel,
        setShowCancel,
        handleCancel,
        isCancelling,
        handleResume,
        isResuming,
        canResume,
    } = useRunDetails();

    if (isLoading) return <Loading />;
    if (isError || !run) {
        return (
            <div className="space-y-4">
                <p className="text-sm text-muted-foreground">This run couldn't be found.</p>
                <Button asChild variant="outline">
                    <Link to={APP_ROUTES.RUNS}>Back to runs</Link>
                </Button>
            </div>
        );
    }

    const status = getRunStatus(run.status);
    const finishedSearches = run.tasks_done + run.tasks_failed + run.tasks_skipped;

    return (
        <div className="space-y-6">
            <Button asChild variant="ghost" size="sm" className="-ml-2">
                <Link to={APP_ROUTES.RUNS}>
                    <ArrowLeft />
                    All runs
                </Link>
            </Button>

            <PageHeader
                title={`Run #${run.id}`}
                description={`${run.profile_name} · ${run.source_keys.map(getSourceLabel).join(", ")}`}
                actions={
                    <>
                        <StatusBadge label={status?.label ?? run.status} className={status?.className} />
                        {isActive && run.status !== "cancelling" && (
                            <Button variant="outline" onClick={() => setShowCancel(true)}>
                                <Ban />
                                Cancel run
                            </Button>
                        )}
                        {canResume && (
                            <Button onClick={handleResume} disabled={isResuming}>
                                <Play />
                                Resume
                            </Button>
                        )}
                        <Button asChild variant="outline">
                            <Link to={APP_ROUTES.LEADS}>
                                <Users />
                                View leads
                            </Link>
                        </Button>
                    </>
                }
            />

            {run.error && (
                <div
                    role="alert"
                    className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm"
                >
                    <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
                    <p>{run.error}</p>
                </div>
            )}

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        Progress
                        {isActive && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
                    </CardTitle>
                    <CardAction>
                        <span className="text-2xl font-semibold tabular-nums">{run.progress_percent}%</span>
                    </CardAction>
                </CardHeader>
                <CardContent className="space-y-5">
                    <Progress value={run.progress_percent} aria-label="Run progress" />

                    <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                        <Stat label="Searches finished" value={`${finishedSearches} / ${run.tasks_total}`} />
                        <Stat label="Failed" value={formatCount(run.tasks_failed)} />
                        <Stat label="Skipped (done recently)" value={formatCount(run.tasks_skipped)} />
                        {run.enrich_total > 0 ? (
                            <Stat label="Websites read" value={`${run.enrich_done} / ${run.enrich_total}`} />
                        ) : (
                            <Stat label="Websites read" value="—" />
                        )}
                    </dl>

                    <dl className="grid grid-cols-2 gap-4 border-t pt-4 text-sm sm:grid-cols-4">
                        <div>
                            <dt className="text-xs text-muted-foreground">Started</dt>
                            <dd>{formatDateTime(run.started_at ?? run.created_at)}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-muted-foreground">Finished</dt>
                            <dd>{run.finished_at ? formatDateTime(run.finished_at) : "—"}</dd>
                        </div>
                        {run.paid_requests_used > 0 && (
                            <div>
                                <dt className="text-xs text-muted-foreground">Billable requests</dt>
                                <dd>
                                    {formatCount(run.paid_requests_used)}
                                    {run.max_paid_requests !== null && ` of ${formatCount(run.max_paid_requests)} allowed`}
                                    <span className="text-muted-foreground"> · about {formatUsd(run.estimated_cost_usd)}</span>
                                </dd>
                            </div>
                        )}
                    </dl>
                </CardContent>
            </Card>

            <section className="space-y-3">
                <h2 className="text-lg font-semibold">Results by source</h2>
                <RunStatsTable run={run} />
            </section>

            <RunTasksTable
                tasks={tasks}
                total={tasksTotal}
                isLoading={isTasksLoading}
                page={taskPage}
                pageSize={taskPageSize}
                status={taskStatus}
                onStatusChange={setTaskStatus}
                onPageChange={setTaskPage}
            />

            <ConfirmationModal
                open={showCancel}
                destructive
                title="Cancel this run?"
                description="It stops after the search it is on. What it has already found is kept."
                confirmText="Cancel run"
                cancelText="Keep running"
                isLoading={isCancelling}
                onConfirm={handleCancel}
                onClose={() => setShowCancel(false)}
            />
        </div>
    );
};

export default RunDetails;
