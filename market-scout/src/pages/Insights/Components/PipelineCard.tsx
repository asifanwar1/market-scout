import { Handshake } from "lucide-react";

import type { TPipeline, TPipelineStage } from "@/api/services/insights/insights.response.types";
import EmptyState from "@/components/custom/EmptyState";
import Stat from "@/components/custom/Stat";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getLeadStatus } from "@/constants/lead-status.constants";
import { getLossReasonLabel } from "@/constants/pipeline.constants";
import { formatCount } from "@/utils/format.utils";
import { formatMoney, formatPercent, percentOf } from "@/utils/pipeline.utils";

const TITLE = "Sales pipeline";
const DESCRIPTION =
    "How far leads have got. 'Reached' counts every lead that got to a stage or beyond, including ones that have since closed.";
const EMPTY_TITLE = "No leads in the pipeline yet";
const EMPTY_DESCRIPTION = "Move leads through Contacted, Interested, Meeting, Quoted and Customer, and this fills in.";
const LOST_REASONS_TITLE = "Why leads were lost";
const MINIMUM_BAR_PERCENT = 2;

type TPipelineCardProps = {
    pipeline: TPipeline | undefined;
};

const PipelineCard = ({ pipeline }: TPipelineCardProps) => {
    if (!pipeline || pipeline.total === 0) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>{TITLE}</CardTitle>
                </CardHeader>
                <CardContent>
                    <EmptyState icon={Handshake} title={EMPTY_TITLE} description={EMPTY_DESCRIPTION} />
                </CardContent>
            </Card>
        );
    }

    const renderStage = (stage: TPipelineStage) => {
        const share = percentOf(stage.reached, pipeline.total);
        return (
            <li key={stage.status} className="space-y-1">
                <div className="flex items-baseline justify-between gap-2 text-sm">
                    <span className="font-medium">{getLeadStatus(stage.status)?.label ?? stage.status}</span>
                    <span className="tabular-nums text-muted-foreground">
                        {formatCount(stage.reached)} reached · {formatCount(stage.current)} here now
                    </span>
                </div>
                <div className="h-2 rounded-full bg-muted">
                    <div className="h-2 rounded-full bg-primary" style={{ width: `${Math.max(share, MINIMUM_BAR_PERCENT)}%` }} />
                </div>
            </li>
        );
    };

    const renderReason = (item: TPipeline["loss_reasons"][number]) => (
        <li key={item.reason ?? "none"} className="flex justify-between gap-2 text-sm">
            <span>{getLossReasonLabel(item.reason)}</span>
            <span className="tabular-nums text-muted-foreground">{formatCount(item.count)}</span>
        </li>
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle>{TITLE}</CardTitle>
                <CardDescription>{DESCRIPTION}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                    <Stat label="Customers won" value={formatCount(pipeline.won)} hint={`${formatCount(pipeline.lost)} lost`} />
                    <Stat label="Win rate" value={formatPercent(pipeline.win_rate)} hint="won of won + lost" />
                    <Stat label="Revenue" value={formatMoney(pipeline.revenue, pipeline.currency)} />
                    <Stat
                        label="Average deal"
                        value={pipeline.average_deal === null ? "—" : formatMoney(pipeline.average_deal, pipeline.currency)}
                        hint={`${formatCount(pipeline.open)} still open`}
                    />
                </dl>

                <ul className="space-y-3">{pipeline.stages.map(renderStage)}</ul>

                {pipeline.loss_reasons.length > 0 && (
                    <div className="space-y-2 border-t pt-4">
                        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{LOST_REASONS_TITLE}</h3>
                        <ul className="space-y-1.5">{pipeline.loss_reasons.map(renderReason)}</ul>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

export default PipelineCard;
