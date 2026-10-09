import { useState } from "react";

import type { TOutcomeInput } from "@/api/services/pipeline/pipeline.request.types";
import type { TOutcome } from "@/api/services/pipeline/pipeline.response.types";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { OUTCOME_NOTE_MAX_LENGTH, PRODUCT_MAX_LENGTH } from "@/constants/limits.constants";
import {
    CLOSING_STATUS,
    LOSS_REASON_OPTIONS,
    type ClosingStatus,
    type LossReason,
} from "@/constants/pipeline.constants";
import { buildOutcomePayload, isAmountValid } from "@/utils/pipeline.utils";

type TOutcomeDialogProps = {
    status: ClosingStatus | null;
    leadName: string;
    currency: string;
    initial: TOutcome | null;
    isSaving: boolean;
    canSkip: boolean;
    onSave: (payload: TOutcomeInput) => void;
    onSkip: () => void;
    onClose: () => void;
};

type TOutcomeFormProps = Omit<TOutcomeDialogProps, "status"> & { status: ClosingStatus };

const WON_TITLE = "Congratulations, a new customer";
const LOST_TITLE = "Why was this lead lost?";
const WON_DESCRIPTION = "Record the deal so reports can show what each source and segment earns. All of this is optional.";
const LOST_DESCRIPTION = "Pick the main reason. Counting reasons shows what to fix.";

const OutcomeForm = ({ status, leadName, currency, initial, isSaving, canSkip, onSave, onSkip, onClose }: TOutcomeFormProps) => {
    const isWon = status === CLOSING_STATUS.WON;
    const [amount, setAmount] = useState(initial?.value != null ? String(initial.value) : "");
    const [product, setProduct] = useState(initial?.product ?? "");
    const [reason, setReason] = useState<LossReason | "">(initial?.loss_reason ?? "");
    const [note, setNote] = useState(initial?.note ?? "");

    const canSave = isWon ? isAmountValid(amount) : reason !== "";
    const amountInvalid = isWon && !isAmountValid(amount);

    const save = () => {
        onSave(buildOutcomePayload(status, { amount, product, reason, note }));
    };

    const onReasonChange = (value: string) => {
        setReason(value as LossReason);
    };

    const renderReason = (option: (typeof LOSS_REASON_OPTIONS)[number]) => (
        <SelectItem key={option.value} value={option.value}>
            {option.label}
        </SelectItem>
    );

    return (
        <DialogContent>
            <DialogHeader>
                <DialogTitle>{isWon ? WON_TITLE : LOST_TITLE}</DialogTitle>
                <DialogDescription>
                    {leadName}. {isWon ? WON_DESCRIPTION : LOST_DESCRIPTION}
                </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
                {isWon ? (
                    <>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label htmlFor="outcome-amount">Deal value ({currency})</Label>
                                <Input
                                    id="outcome-amount"
                                    inputMode="decimal"
                                    value={amount}
                                    placeholder="e.g. 1500"
                                    aria-invalid={amountInvalid}
                                    onChange={(event) => setAmount(event.target.value)}
                                />
                                {amountInvalid && <p className="text-sm text-destructive">Enter a number, or leave it blank.</p>}
                            </div>
                            <div className="space-y-1.5">
                                <Label htmlFor="outcome-product">Product</Label>
                                <Input
                                    id="outcome-product"
                                    maxLength={PRODUCT_MAX_LENGTH}
                                    value={product}
                                    placeholder="What they bought"
                                    onChange={(event) => setProduct(event.target.value)}
                                />
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="space-y-1.5">
                        <Label htmlFor="outcome-reason">Reason</Label>
                        <Select value={reason} onValueChange={onReasonChange}>
                            <SelectTrigger id="outcome-reason" className="w-full">
                                <SelectValue placeholder="Choose a reason" />
                            </SelectTrigger>
                            <SelectContent>{LOSS_REASON_OPTIONS.map(renderReason)}</SelectContent>
                        </Select>
                    </div>
                )}
                <div className="space-y-1.5">
                    <Label htmlFor="outcome-note">Note (optional)</Label>
                    <Textarea
                        id="outcome-note"
                        rows={3}
                        maxLength={OUTCOME_NOTE_MAX_LENGTH}
                        value={note}
                        onChange={(event) => setNote(event.target.value)}
                    />
                </div>
            </div>

            <DialogFooter>
                <Button variant="ghost" disabled={isSaving} onClick={onClose}>
                    Cancel
                </Button>
                {canSkip && (
                    <Button variant="outline" disabled={isSaving} onClick={onSkip}>
                        Skip details
                    </Button>
                )}
                <Button disabled={!canSave || isSaving} onClick={save}>
                    {isSaving ? "Saving…" : "Save"}
                </Button>
            </DialogFooter>
        </DialogContent>
    );
};

const OutcomeDialog = ({ status, onClose, ...rest }: TOutcomeDialogProps) => {
    const onOpenChange = (next: boolean) => {
        if (!next && !rest.isSaving) onClose();
    };

    return (
        <Dialog open={status !== null} onOpenChange={onOpenChange}>
            {status !== null && <OutcomeForm status={status} onClose={onClose} {...rest} />}
        </Dialog>
    );
};

export default OutcomeDialog;
