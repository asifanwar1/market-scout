import { AlertTriangle, CalendarClock, Loader2, Play } from "lucide-react";

import type { TRunEstimate, TSourceEstimate } from "@/api/services/runs/runs.response.types";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCount, formatUsd, pluralize } from "@/utils/format.utils";

type TEstimatePanelProps = {
    hasSelection: boolean;
    estimate: TRunEstimate | undefined;
    isEstimating: boolean;
    error: string | null;
    canStart: boolean;
    isStarting: boolean;
    onStart: () => void;
    isRepeating: boolean;
};

const EstimatePanel = ({
    hasSelection,
    estimate,
    isEstimating,
    error,
    canStart,
    isStarting,
    onStart,
    isRepeating,
}: TEstimatePanelProps) => {
    const renderWarning = (warning: string) => (
        <li
            key={warning}
            className="flex items-start gap-2 rounded-md bg-warning p-2.5 text-xs text-warning-foreground"
        >
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
            {warning}
        </li>
    );
    const renderSource = (source: TSourceEstimate) => (
        <li key={source.source_key} className="flex justify-between gap-2">
            <span>{source.name}</span>
            <span className="text-right text-muted-foreground tabular-nums">
                {pluralize(source.tasks - source.tasks_skipped, "search", "searches")}
                {source.max_requests !== null &&
                    ` · up to ${formatCount(source.max_requests)} billable requests`}
            </span>
        </li>
    );
    return (
        <Card className="lg:sticky lg:top-20">
            <CardHeader>
                <CardTitle>{isRepeating ? "What each run will do" : "What this run will do"}</CardTitle>
                {isEstimating && hasSelection && (
                    <CardAction>
                        <Loader2 className="size-4 animate-spin text-muted-foreground" />
                    </CardAction>
                )}
            </CardHeader>
            <CardContent className="space-y-4">
                {!hasSelection && (
                    <p className="text-sm text-muted-foreground">
                        Choose at least one city, one segment and one source to see how many searches
                        this will take, how long, and what it may cost.
                    </p>
                )}

                {hasSelection && error && (
                    <div
                        role="alert"
                        className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm"
                    >
                        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
                        <p>{error}</p>
                    </div>
                )}

                {hasSelection && !error && estimate && (
                    <>
                        <dl className="grid grid-cols-3 gap-3">
                            <div>
                                <dt className="text-xs text-muted-foreground">Searches</dt>
                                <dd className="text-2xl font-semibold tabular-nums">
                                    {formatCount(estimate.tasks_to_run)}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-muted-foreground">Time</dt>
                                <dd className="text-2xl font-semibold tabular-nums">
                                    {estimate.estimated_minutes === 0 ? "—" : `~${estimate.estimated_minutes} min`}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-muted-foreground">Cost</dt>
                                <dd className="text-2xl font-semibold tabular-nums">
                                    {estimate.paid_requests_max > 0 ? `≤ ${formatUsd(estimate.estimated_cost_usd)}` : "Free"}
                                </dd>
                            </div>
                        </dl>

                        <ul className="space-y-1.5 border-t pt-3 text-sm">
                            {estimate.by_source.map(renderSource)}
                        </ul>

                        {estimate.warnings.length > 0 && (
                            <ul className="space-y-2">
                                {estimate.warnings.map(renderWarning)}
                            </ul>
                        )}

                        {!isRepeating && estimate.tasks_total > 0 && estimate.tasks_to_run === 0 && (
                            <p className="text-sm text-muted-foreground">
                                Everything here was searched recently. Turn on "Search again" to repeat it.
                            </p>
                        )}
                    </>
                )}

                <Button className="w-full" size="lg" disabled={!canStart || isStarting} onClick={onStart}>
                    {isStarting ? <Loader2 className="animate-spin" /> : isRepeating ? <CalendarClock /> : <Play />}
                    {isRepeating ? "Save repeating search" : "Start run"}
                </Button>
            </CardContent>
        </Card>
    );
};

export default EstimatePanel;
