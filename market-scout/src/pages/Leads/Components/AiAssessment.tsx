import { Sparkles } from "lucide-react";
import { useState } from "react";

import type { TBusinessDetail } from "@/api/services/businesses/businesses.response.types";
import ScoreBadge from "@/components/custom/ScoreBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AI_ANALYSIS_STATUS, AI_FIT_TITLE, CONFIDENCE_LABELS } from "@/constants/ai.constants";
import { useApplyAiSegment, useGetAiStatus } from "@/hooks/api/ai.queries";
import { showToast } from "@/lib/toast";
import { getAiModelLabel } from "@/utils/ai.utils";
import { formatDate } from "@/utils/format.utils";
import AnalyzeDialog from "./AnalyzeDialog";

const NOT_ANALYSED_TEXT = "Not analysed yet. The AI reads this business's website and rates how well it fits your ideal customer.";
const NO_SCORE_TEXT = "Too little on the site to rate";
const TRUNCATED_TEXT = "Only the first part of the site was read.";
const NO_WEBSITE_HINT = "This lead has no website, so there is nothing for the AI to read.";

type TAiAssessmentProps = {
    lead: TBusinessDetail;
};

const AiAssessment = ({ lead }: TAiAssessmentProps) => {
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const { data: status } = useGetAiStatus();
    const { mutateAsync: applySegment, isPending: isApplying } = useApplyAiSegment();

    const ai = lead.ai;
    const profileId = lead.classifications[0]?.profile_id;
    const isReady = status?.is_ready === true;
    const canAnalyze = isReady && profileId !== undefined && lead.website !== null;
    const isOk = ai?.status === AI_ANALYSIS_STATUS.OK;
    const canApply = isOk && ai.segment_slug !== null && ai.segment_slug !== ai.current_segment_slug;
    const hint = !isReady ? status?.reason : lead.website === null ? NO_WEBSITE_HINT : null;

    const openDialog = () => {
        setIsDialogOpen(true);
    };

    const closeDialog = () => {
        setIsDialogOpen(false);
    };

    const apply = async () => {
        if (!ai) return;
        await applySegment({ id: lead.id, body: { profile_id: ai.profile_id } });
        showToast.success(`Segment changed to ${ai.segment_name}`);
    };

    return (
        <div className="space-y-3">
            {!ai && <p className="text-sm text-muted-foreground">{NOT_ANALYSED_TEXT}</p>}

            {ai && isOk && (
                <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                        {ai.fit_score !== null ? <ScoreBadge score={ai.fit_score} title={AI_FIT_TITLE} /> : <span className="text-sm text-muted-foreground">{NO_SCORE_TEXT}</span>}
                        {ai.confidence && <Badge variant="outline">{CONFIDENCE_LABELS[ai.confidence] ?? ai.confidence}</Badge>}
                    </div>
                    {ai.summary && <p className="text-sm">{ai.summary}</p>}
                    {ai.fit_reason && <p className="text-sm text-muted-foreground">{ai.fit_reason}</p>}
                    {ai.segment_name && (
                        <div className="space-y-1 rounded-md border bg-muted/40 p-3 text-sm">
                            <p>
                                <span className="font-medium">Suggested segment:</span> {ai.segment_name}
                            </p>
                            {ai.segment_reason && <p className="text-muted-foreground">{ai.segment_reason}</p>}
                            {canApply ? (
                                <Button size="sm" variant="outline" disabled={isApplying} onClick={apply}>
                                    Use this segment
                                </Button>
                            ) : (
                                <p className="text-xs text-muted-foreground">Already this lead's segment.</p>
                            )}
                        </div>
                    )}
                    <p className="text-xs text-muted-foreground">
                        Analysed {formatDate(ai.analyzed_at)} by {getAiModelLabel(ai.model)} · {ai.pages_read} {ai.pages_read === 1 ? "page" : "pages"} read
                        {ai.truncated && ` · ${TRUNCATED_TEXT}`}
                    </p>
                </div>
            )}

            {ai && !isOk && <p className="text-sm text-muted-foreground">{ai.error}</p>}

            <Button size="sm" variant="outline" disabled={!canAnalyze} onClick={openDialog}>
                <Sparkles />
                {ai ? "Analyze again" : "Analyze with AI"}
            </Button>
            {hint && <p className="text-xs text-muted-foreground">{hint}</p>}

            <AnalyzeDialog leadIds={isDialogOpen ? [lead.id] : []} profileId={profileId} refreshByDefault={ai !== null} onClose={closeDialog} />
        </div>
    );
};

export default AiAssessment;
