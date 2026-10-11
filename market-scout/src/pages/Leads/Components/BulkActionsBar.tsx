import { ShieldCheck, Sparkles, Trash2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { LEAD_STATUS_OPTIONS } from "@/constants";
import type { LeadStatus } from "@/constants/lead-status.constants";
import { BULK_DELETE_BUTTON_LABEL } from "../Leads.constants";
import type { TLeadsPage } from "../Leads.Container";

const UNASSIGN = "none";

type TBulkActionsBarProps = {
    page: TLeadsPage;
};

const BulkActionsBar = ({ page }: TBulkActionsBarProps) => {
    const {
        isAdmin,
        selectedIds,
        assignees,
        activeProfileId,
        applyBulkUpdate,
        isBulkUpdating,
        openAnalyze,
        openCheck,
        openBulkDelete,
        setRowSelection,
    } = page;
    const count = selectedIds.length;

    if (count === 0) return null;

    const renderStatusOption = (option: (typeof LEAD_STATUS_OPTIONS)[number]) => (
        <SelectItem key={option.value} value={option.value}>
            {option.label}
        </SelectItem>
    );
    const renderUser = (user: (typeof assignees)[number]) => (
        <SelectItem key={user.id} value={String(user.id)}>
            {user.full_name}
        </SelectItem>
    );
    return (
        <div
            role="region"
            aria-label="Actions for selected leads"
            className="flex flex-wrap items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2"
        >
            <span className="text-sm font-medium">
                {count} lead{count === 1 ? "" : "s"} selected
            </span>

            <Select
                value=""
                disabled={isBulkUpdating}
                onValueChange={(value) =>
                    void applyBulkUpdate(
                        { assigned_to_id: value === UNASSIGN ? null : Number(value) },
                        value === UNASSIGN ? "Unassigned" : "Assigned",
                    )
                }
            >
                <SelectTrigger size="sm" className="w-44" aria-label="Assign selected leads to">
                    <SelectValue placeholder="Assign to…" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value={UNASSIGN}>Unassign</SelectItem>
                    {assignees.map(renderUser)}
                </SelectContent>
            </Select>

            <Select
                value=""
                disabled={isBulkUpdating}
                onValueChange={(value) =>
                    void applyBulkUpdate({ lead_status: value as LeadStatus }, "Status changed")
                }
            >
                <SelectTrigger size="sm" className="w-44" aria-label="Set status of selected leads">
                    <SelectValue placeholder="Set status…" />
                </SelectTrigger>
                <SelectContent>
                    {LEAD_STATUS_OPTIONS.map(renderStatusOption)}
                </SelectContent>
            </Select>

            <Button variant="outline" size="sm" disabled={!activeProfileId} onClick={openAnalyze}>
                <Sparkles />
                Analyze with AI
            </Button>

            <Button variant="outline" size="sm" onClick={openCheck}>
                <ShieldCheck />
                Check contacts
            </Button>

            {isAdmin && (
                <Button variant="destructive" size="sm" onClick={openBulkDelete}>
                    <Trash2 />
                    {BULK_DELETE_BUTTON_LABEL}
                </Button>
            )}

            <Button variant="ghost" size="sm" onClick={() => setRowSelection({})}>
                <X />
                Clear selection
            </Button>
        </div>
    );
};

export default BulkActionsBar;
