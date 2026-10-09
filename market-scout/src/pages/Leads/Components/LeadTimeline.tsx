import {
    ArrowRightLeft,
    BadgeDollarSign,
    CheckCircle2,
    Mail,
    MessageCircle,
    Phone,
    Plus,
    StickyNote,
    UserRound,
    Users,
    type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import type { TActivity } from "@/api/services/pipeline/pipeline.response.types";
import Loading from "@/components/custom/Loading";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ACTIVITY_SUMMARY_MAX_LENGTH } from "@/constants/limits.constants";
import { ACTIVITY_KIND, MANUAL_ACTIVITY_OPTIONS, type ActivityKind, type ManualActivityKind } from "@/constants/pipeline.constants";
import { useAddActivity, useGetActivities } from "@/hooks/api/pipeline.queries";
import { showToast } from "@/lib/toast";
import { formatDateTime, formatRelative } from "@/utils/format.utils";
import { describeActivity } from "@/utils/pipeline.utils";

const ACTIVITY_ICONS: Record<ActivityKind, LucideIcon> = {
    [ACTIVITY_KIND.NOTE]: StickyNote,
    [ACTIVITY_KIND.CALL]: Phone,
    [ACTIVITY_KIND.WHATSAPP]: MessageCircle,
    [ACTIVITY_KIND.EMAIL]: Mail,
    [ACTIVITY_KIND.MEETING]: Users,
    [ACTIVITY_KIND.STATUS_CHANGE]: ArrowRightLeft,
    [ACTIVITY_KIND.ASSIGNMENT]: UserRound,
    [ACTIVITY_KIND.TASK_COMPLETED]: CheckCircle2,
    [ACTIVITY_KIND.OUTCOME_UPDATED]: BadgeDollarSign,
};

const EMPTY_TEXT = "Nothing logged yet. Log a call or note, and status changes will appear here automatically.";
const PLACEHOLDER = "What happened? e.g. Spoke to the owner, wants a quote by Friday";
const SYSTEM_PERSON = "System";

type TLeadTimelineProps = {
    businessId: number;
};

const LeadTimeline = ({ businessId }: TLeadTimelineProps) => {
    const { data, isPending } = useGetActivities(businessId);
    const { mutateAsync: addActivity, isPending: isAdding } = useAddActivity();

    const [kind, setKind] = useState<ManualActivityKind>(ACTIVITY_KIND.CALL);
    const [summary, setSummary] = useState("");

    const entries = data?.data ?? [];
    const canAdd = summary.trim().length > 0 && !isAdding;

    const onKindChange = (value: string) => {
        setKind(value as ManualActivityKind);
    };

    const submit = async () => {
        await addActivity({ id: businessId, body: { kind, summary: summary.trim() } });
        setSummary("");
        showToast.success("Logged");
    };

    const renderKind = (option: (typeof MANUAL_ACTIVITY_OPTIONS)[number]) => (
        <SelectItem key={option.value} value={option.value}>
            {option.label}
        </SelectItem>
    );

    const renderEntry = (entry: TActivity) => {
        const Icon = ACTIVITY_ICONS[entry.kind];
        const view = describeActivity(entry);
        return (
            <li key={entry.id} className="flex gap-3">
                <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1 space-y-0.5">
                    <p className="text-sm font-medium">{view.title}</p>
                    {view.detail && <p className="whitespace-pre-wrap break-words text-sm text-muted-foreground">{view.detail}</p>}
                    <p className="text-xs text-muted-foreground" title={formatDateTime(entry.created_at)}>
                        {entry.created_by?.full_name ?? SYSTEM_PERSON} · {formatRelative(entry.created_at)}
                    </p>
                </div>
            </li>
        );
    };

    return (
        <div className="space-y-4">
            <div className="space-y-2">
                <div className="flex gap-2">
                    <Select value={kind} onValueChange={onKindChange}>
                        <SelectTrigger className="w-36" aria-label="Type of entry">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>{MANUAL_ACTIVITY_OPTIONS.map(renderKind)}</SelectContent>
                    </Select>
                    <Button size="sm" className="ml-auto self-center" disabled={!canAdd} onClick={submit}>
                        <Plus />
                        Log it
                    </Button>
                </div>
                <Textarea
                    rows={2}
                    maxLength={ACTIVITY_SUMMARY_MAX_LENGTH}
                    value={summary}
                    placeholder={PLACEHOLDER}
                    aria-label="What happened"
                    onChange={(event) => setSummary(event.target.value)}
                />
            </div>

            {isPending ? (
                <Loading />
            ) : entries.length === 0 ? (
                <p className="text-sm text-muted-foreground">{EMPTY_TEXT}</p>
            ) : (
                <ul className="space-y-4">{entries.map(renderEntry)}</ul>
            )}
        </div>
    );
};

export default LeadTimeline;
