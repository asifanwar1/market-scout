import { AlertTriangle, ArrowLeft, Ban, Loader2, Play, Users } from "lucide-react";
import { Link } from "react-router-dom";

import ConfirmationModal from "@/components/custom/ConfirmationModal";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import Stat from "@/components/custom/Stat";
import StatusBadge from "@/components/custom/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { APP_ROUTES } from "@/routes/appRoutes";
import RunStatsTable from "./Components/RunStatsTable";
import RunTasksTable from "./Components/RunTasksTable";
import { CANCEL_RUN_DESCRIPTION } from "./RunDetails.constants";
import { useRunDetails } from "./RunDetails.Container";

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
        statusLabel,
        statusClassName,
        pageTitle,
        pageDescription,
        searchesFinishedText,
        websitesReadText,
        startedText,
        finishedText,
        hasBillableRequests,
        billableText,
        estimatedCostText,
        canCancel,
        failedText,
        skippedText,
        setTaskStatus,
        setTaskPage,
        showCancel,
        openCancel,
        closeCancel,
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

    return (
        <div className="space-y-6">
            <Button asChild variant="ghost" size="sm" className="-ml-2">
                <Link to={APP_ROUTES.RUNS}>
                    <ArrowLeft />
                    All runs
                </Link>
            </Button>

            <PageHeader
                title={pageTitle}
                description={pageDescription}
                actions={
                    <>
                        <StatusBadge label={statusLabel} className={statusClassName} />
                        {canCancel && (
                            <Button variant="outline" onClick={openCancel}>
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
                <div role="alert" className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm">
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
                        <Stat label="Searches finished" value={searchesFinishedText} />
                        <Stat label="Failed" value={failedText} />
                        <Stat label="Skipped (done recently)" value={skippedText} />
                        <Stat label="Websites read" value={websitesReadText} />
                    </dl>

                    <dl className="grid grid-cols-2 gap-4 border-t pt-4 text-sm sm:grid-cols-4">
                        <div>
                            <dt className="text-xs text-muted-foreground">Started</dt>
                            <dd>{startedText}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-muted-foreground">Finished</dt>
                            <dd>{finishedText}</dd>
                        </div>
                        {hasBillableRequests && (
                            <div>
                                <dt className="text-xs text-muted-foreground">Billable requests</dt>
                                <dd>
                                    {billableText}
                                    <span className="text-muted-foreground"> · {estimatedCostText}</span>
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
                description={CANCEL_RUN_DESCRIPTION}
                confirmText="Cancel run"
                cancelText="Keep running"
                isLoading={isCancelling}
                onConfirm={handleCancel}
                onClose={closeCancel}
            />
        </div>
    );
};

export default RunDetails;
