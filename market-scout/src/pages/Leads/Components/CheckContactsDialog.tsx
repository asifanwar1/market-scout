import { Loader2, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { ACTIVE_QUALITY_TASK_STATUSES, QUALITY_TASK_STATUS } from "@/constants/quality.constants";
import { useGetQualityTask, useStartChecks } from "@/hooks/api/quality.queries";
import { pluralize } from "@/utils/format.utils";
import { describeCheckCounts } from "@/utils/quality.utils";

const TITLE = "Check contacts";
const WHAT_IT_DOES =
    "For each lead, this looks up whether the email's domain can receive mail, visits the website once to see whether it answers, and flags phone numbers listed for many businesses. It never sends an email or message. Emails that cannot receive mail and websites that are down stop counting towards the score.";
const REFRESH_LABEL = "Check again even if checked in the last 30 days";
const SEPARATOR = ", ";
const PERCENT = 100;

type TCheckContactsDialogProps = {
    leadIds: number[];
    onClose: () => void;
};

const CheckFlow = ({ leadIds, onClose }: TCheckContactsDialogProps) => {
    const [refresh, setRefresh] = useState(false);
    const [taskId, setTaskId] = useState<number | null>(null);
    const { mutateAsync: start, isPending: isStarting } = useStartChecks();
    const { data: task } = useGetQualityTask(taskId);

    const isRunning = task !== undefined && ACTIVE_QUALITY_TASK_STATUSES.includes(task.status);
    const isFinished = task !== undefined && !isRunning;
    const progress = task && task.total > 0 ? Math.round((PERCENT * task.done) / task.total) : 0;
    const summary = task ? describeCheckCounts(task.counts) : [];

    const begin = async () => {
        const created = await start({ business_ids: leadIds, refresh });
        setTaskId(created.id);
    };

    return (
        <DialogContent>
            <DialogHeader>
                <DialogTitle>{TITLE}</DialogTitle>
                <DialogDescription>{pluralize(leadIds.length, "lead", "leads")} selected.</DialogDescription>
            </DialogHeader>

            {task ? (
                <div className="space-y-3">
                    <Progress value={progress} aria-label="Progress" />
                    <p className="text-sm">
                        {isRunning ? "Checking… " : ""}
                        {pluralize(task.done, "lead", "leads")} of {task.total} checked
                    </p>
                    {isFinished && (
                        <p className="text-sm font-medium">
                            {task.status === QUALITY_TASK_STATUS.FAILED ? task.error : summary.join(SEPARATOR) || "Everything checked out, or was checked recently."}
                        </p>
                    )}
                </div>
            ) : (
                <div className="space-y-3 text-sm">
                    <p className="text-muted-foreground">{WHAT_IT_DOES}</p>
                    <div className="flex items-center gap-2">
                        <Checkbox id="check-refresh" checked={refresh} onCheckedChange={(checked) => setRefresh(checked === true)} />
                        <Label htmlFor="check-refresh" className="font-normal">
                            {REFRESH_LABEL}
                        </Label>
                    </div>
                </div>
            )}

            <DialogFooter>
                {isFinished ? (
                    <Button onClick={onClose}>Done</Button>
                ) : (
                    <>
                        <Button variant="ghost" onClick={onClose}>
                            {isRunning ? "Close (keeps running)" : "Cancel"}
                        </Button>
                        {task === undefined && (
                            <Button disabled={isStarting} onClick={begin}>
                                {isStarting ? <Loader2 className="animate-spin" /> : <ShieldCheck />}
                                Start
                            </Button>
                        )}
                    </>
                )}
            </DialogFooter>
        </DialogContent>
    );
};

const CheckContactsDialog = ({ leadIds, onClose }: TCheckContactsDialogProps) => {
    const isOpen = leadIds.length > 0;

    const onOpenChange = (next: boolean) => {
        if (!next) onClose();
    };

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            {isOpen && <CheckFlow leadIds={leadIds} onClose={onClose} />}
        </Dialog>
    );
};

export default CheckContactsDialog;
