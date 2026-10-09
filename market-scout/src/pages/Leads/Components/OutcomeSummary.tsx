import { Pencil } from "lucide-react";

import type { TOutcome } from "@/api/services/pipeline/pipeline.response.types";
import { Button } from "@/components/ui/button";
import { OUTCOME_KIND, getLossReasonLabel } from "@/constants/pipeline.constants";
import { formatDate } from "@/utils/format.utils";
import { formatMoney } from "@/utils/pipeline.utils";

const WON_LABEL = "Won";
const LOST_LABEL = "Lost";
const NO_DEAL_DETAILS = "No deal details recorded";
const SEPARATOR = " · ";

type TOutcomeSummaryProps = {
    outcome: TOutcome;
    currency: string;
    onEdit: () => void;
};

const OutcomeSummary = ({ outcome, currency, onEdit }: TOutcomeSummaryProps) => {
    const isWon = outcome.kind === OUTCOME_KIND.WON;
    const dealParts = [outcome.value !== null ? formatMoney(outcome.value, currency) : null, outcome.product].filter(Boolean);
    const headline = isWon ? dealParts.join(SEPARATOR) || NO_DEAL_DETAILS : getLossReasonLabel(outcome.loss_reason);
    const closedBy = outcome.closed_by ? ` by ${outcome.closed_by.full_name}` : "";

    return (
        <div className="space-y-1 rounded-md border bg-muted/40 p-3">
            <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium">
                    <span className={isWon ? "text-success-foreground" : "text-muted-foreground"}>{isWon ? WON_LABEL : LOST_LABEL}</span>
                    {SEPARATOR}
                    {headline}
                </p>
                <Button variant="ghost" size="icon-xs" aria-label="Edit deal details" onClick={onEdit}>
                    <Pencil />
                </Button>
            </div>
            {outcome.note && <p className="whitespace-pre-wrap break-words text-sm text-muted-foreground">{outcome.note}</p>}
            <p className="text-xs text-muted-foreground">
                Closed {formatDate(outcome.closed_at)}
                {closedBy}
            </p>
        </div>
    );
};

export default OutcomeSummary;
