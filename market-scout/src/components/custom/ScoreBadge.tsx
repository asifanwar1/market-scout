import { cn } from "@/lib/utils";
import { SCORE_HIGH_MIN, SCORE_MEDIUM_MIN } from "@/constants/limits.constants";

type TScoreBadgeProps = {
    score: number | null | undefined;
};

const toneFor = (score: number) => {
    if (score >= SCORE_HIGH_MIN) return "bg-success text-success-foreground";
    if (score >= SCORE_MEDIUM_MIN) return "bg-warning text-warning-foreground";
    return "bg-muted text-muted-foreground";
};

const ScoreBadge = ({ score }: TScoreBadgeProps) => {
    if (score === null || score === undefined) {
        return <span className="text-muted-foreground">—</span>;
    }

    return (
        <span
            title="Lead score: how much usable contact detail we have"
            className={cn(
                "inline-flex min-w-9 items-center justify-center rounded-md px-2 py-0.5 text-xs font-semibold tabular-nums",
                toneFor(score),
            )}
        >
            {score}
        </span>
    );
};

export default ScoreBadge;
