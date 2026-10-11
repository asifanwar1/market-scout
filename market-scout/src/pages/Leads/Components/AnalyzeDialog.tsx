import { Loader2, Sparkles } from "lucide-react";
import { useState } from "react";

import Loading from "@/components/custom/Loading";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { ACTIVE_AI_BATCH_STATUSES, AI_BATCH_STATUS, SHOWN_ERROR_SAMPLES } from "@/constants/ai.constants";
import { useEstimateAi, useGetAiBatch, useGetAiStatus, useStartAiAnalysis } from "@/hooks/api/ai.queries";
import { batchProgress, describeBatch, formatAiCost } from "@/utils/ai.utils";
import { pluralize } from "@/utils/format.utils";

const TITLE = "Analyze with AI";
const NO_PROFILE_TEXT = "Choose a profile first. The AI scores leads against that profile's ideal customer.";
const WORST_CASE_NOTE = "This is the most it could cost. Most leads cost a fraction of it, and nothing is charged for leads it skips.";
const REFRESH_LABEL = "Analyze again even if a lead was already analysed";
const SEPARATOR = ", ";

type TAnalyzeDialogProps = {
    leadIds: number[];
    profileId: number | undefined;
    refreshByDefault?: boolean;
    onClose: () => void;
};

type TAnalyzeFlowProps = Omit<TAnalyzeDialogProps, "refreshByDefault"> & { refreshByDefault: boolean };

const AnalyzeFlow = ({ leadIds, profileId, refreshByDefault, onClose }: TAnalyzeFlowProps) => {
    const [refresh, setRefresh] = useState(refreshByDefault);
    const [batchId, setBatchId] = useState<number | null>(null);

    const { data: status } = useGetAiStatus();
    const canEstimate = profileId !== undefined && batchId === null && status?.is_ready === true;
    const { data: estimate, isPending: isEstimating } = useEstimateAi(
        canEstimate ? { business_ids: leadIds, profile_id: profileId, refresh } : null,
    );
    const { mutateAsync: start, isPending: isStarting } = useStartAiAnalysis();
    const { data: batch } = useGetAiBatch(batchId);

    const isRunning = batch !== undefined && ACTIVE_AI_BATCH_STATUSES.includes(batch.status);
    const isFinished = batch !== undefined && !isRunning;
    const canStart = estimate !== undefined && estimate.to_analyze > 0 && !isStarting;

    const begin = async () => {
        if (profileId === undefined) return;
        const created = await start({ business_ids: leadIds, profile_id: profileId, refresh });
        setBatchId(created.id);
    };

    const renderWarning = (warning: string) => (
        <li key={warning} className="text-sm text-muted-foreground">
            {warning}
        </li>
    );
    const renderSample = (sample: string) => (
        <li key={sample} className="break-words">
            {sample}
        </li>
    );

    const renderBody = () => {
        if (profileId === undefined) return <p className="text-sm text-muted-foreground">{NO_PROFILE_TEXT}</p>;
        if (!status) return <Loading />;
        if (!status.is_ready) return <p className="text-sm">{status.reason}</p>;

        if (batch) {
            return (
                <div className="space-y-3">
                    <Progress value={batchProgress(batch)} aria-label="Progress" />
                    <p className="text-sm">
                        {isRunning ? "Reading websites and asking the AI… " : ""}
                        {pluralize(batch.done, "lead", "leads")} of {batch.total} handled · {formatAiCost(batch.spent_usd)} spent
                    </p>
                    {isFinished && (
                        <div className="space-y-2 text-sm">
                            <p className="font-medium">{describeBatch(batch).join(SEPARATOR) || "Nothing to do."}</p>
                            {batch.status === AI_BATCH_STATUS.STOPPED && batch.error && <p className="text-destructive">{batch.error}</p>}
                            {batch.status === AI_BATCH_STATUS.FAILED && batch.error && <p className="text-destructive">{batch.error}</p>}
                            {batch.error_samples.length > 0 && (
                                <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                                    {batch.error_samples.slice(0, SHOWN_ERROR_SAMPLES).map(renderSample)}
                                </ul>
                            )}
                        </div>
                    )}
                </div>
            );
        }

        if (isEstimating || !estimate) return <Loading />;

        return (
            <div className="space-y-3 text-sm">
                <p>
                    <span className="font-medium">{pluralize(estimate.to_analyze, "lead", "leads")}</span> will be read and rated by{" "}
                    {estimate.model_label}, for up to <span className="font-medium">{formatAiCost(estimate.estimated_cost_usd)}</span>.
                </p>
                <p className="text-muted-foreground">
                    {WORST_CASE_NOTE} {formatAiCost(estimate.remaining_usd)} is left of this month's budget.
                </p>
                {estimate.warnings.length > 0 && <ul className="space-y-1">{estimate.warnings.map(renderWarning)}</ul>}
                <div className="flex items-center gap-2">
                    <Checkbox id="analyze-refresh" checked={refresh} onCheckedChange={(checked) => setRefresh(checked === true)} />
                    <Label htmlFor="analyze-refresh" className="font-normal">
                        {REFRESH_LABEL}
                    </Label>
                </div>
            </div>
        );
    };

    return (
        <DialogContent>
            <DialogHeader>
                <DialogTitle>{TITLE}</DialogTitle>
                <DialogDescription>
                    {pluralize(leadIds.length, "lead", "leads")} selected. The AI reads each lead's website and rates how well it fits your ideal customer.
                </DialogDescription>
            </DialogHeader>

            {renderBody()}

            <DialogFooter>
                {isFinished ? (
                    <Button onClick={onClose}>Done</Button>
                ) : (
                    <>
                        <Button variant="ghost" onClick={onClose}>
                            {isRunning ? "Close (keeps running)" : "Cancel"}
                        </Button>
                        {batch === undefined && (
                            <Button disabled={!canStart} onClick={begin}>
                                {isStarting ? <Loader2 className="animate-spin" /> : <Sparkles />}
                                Start
                            </Button>
                        )}
                    </>
                )}
            </DialogFooter>
        </DialogContent>
    );
};

const AnalyzeDialog = ({ leadIds, profileId, refreshByDefault = false, onClose }: TAnalyzeDialogProps) => {
    const isOpen = leadIds.length > 0;

    const onOpenChange = (next: boolean) => {
        if (!next) onClose();
    };

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            {isOpen && <AnalyzeFlow leadIds={leadIds} profileId={profileId} refreshByDefault={refreshByDefault} onClose={onClose} />}
        </Dialog>
    );
};

export default AnalyzeDialog;
