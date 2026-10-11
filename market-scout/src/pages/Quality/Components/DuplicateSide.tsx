import { Button } from "@/components/ui/button";
import type { TDuplicateSide } from "@/api/services/quality/quality.response.types";
import { formatPhone, getSourceLabel } from "@/utils/format.utils";

type TDuplicateSideProps = {
    label: string;
    side: TDuplicateSide;
    isBusy: boolean;
    onKeep: (side: TDuplicateSide) => void;
};

const Detail = ({ label, value }: { label: string; value: string | null }) => (
    <div className="flex gap-2 text-xs">
        <dt className="w-16 shrink-0 text-muted-foreground">{label}</dt>
        <dd className="min-w-0 break-words">{value || "—"}</dd>
    </div>
);

const DuplicateSide = ({ label, side, isBusy, onKeep }: TDuplicateSideProps) => {
    return (
        <div className="min-w-0 space-y-2 rounded-md border p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
            <p className="break-words font-medium">{side.name}</p>
            <dl className="space-y-1">
                <Detail label="City" value={side.city} />
                <Detail label="Address" value={side.address} />
                <Detail label="Phones" value={side.phones.map(formatPhone).join(", ")} />
                <Detail label="Emails" value={side.emails.join(", ")} />
                <Detail label="Website" value={side.website} />
                <Detail label="Sources" value={side.sources.map(getSourceLabel).join(", ")} />
                <Detail label="Status" value={`${side.lead_status}${side.assigned_to ? ` · ${side.assigned_to}` : ""}`} />
                <Detail label="Score" value={side.score === null ? null : String(side.score)} />
            </dl>
            <Button size="sm" variant="outline" disabled={isBusy} onClick={() => onKeep(side)}>
                Keep this one
            </Button>
        </div>
    );
};

export default DuplicateSide;
