import { cn } from "@/lib/utils";

type TScoreBadgeProps = {
    score: number | null | undefined;
};

// A lead's score is 0-100: how much is known that a salesperson can act on.
const toneFor = (score: number) => {
    if (score >= 70) return "bg-success text-success-foreground";
    if (score >= 40) return "bg-warning text-warning-foreground";
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
