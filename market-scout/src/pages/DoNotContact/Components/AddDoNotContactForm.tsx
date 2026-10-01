"use no memo";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { Controller, useForm, useWatch } from "react-hook-form";

import type { TDoNotContactBody } from "@/api/services/businesses/businesses.request.types";
import { Button } from "@/components/ui/button";
import { DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useAddDoNotContact } from "@/hooks/api/compliance.queries";
import { showToast } from "@/lib/toast";
import { DO_NOT_CONTACT_KIND, REASON_MAX_LENGTH } from "../DoNotContact.constants";
import { addDoNotContactSchema, EMPTY_ADD_FORM, type TAddFormValues } from "./AddDoNotContactForm.schema";

type TAddDoNotContactFormProps = {
    onClose: () => void;
};

const buildAddPayload = (values: TAddFormValues): TDoNotContactBody => ({
    ...(values.kind === DO_NOT_CONTACT_KIND.PHONE ? { phone: values.value } : { email: values.value }),
    reason: values.reason.trim() || null,
});

const AddDoNotContactForm = ({ onClose }: TAddDoNotContactFormProps) => {
    const { mutateAsync: add, isPending } = useAddDoNotContact();
    const {
        register,
        control,
        handleSubmit,
        formState: { errors },
    } = useForm<TAddFormValues>({
        resolver: zodResolver(addDoNotContactSchema),
        defaultValues: EMPTY_ADD_FORM,
    });
    const kind = useWatch({ control, name: "kind" });
    const isPhone = kind === DO_NOT_CONTACT_KIND.PHONE;

    const onSubmit = handleSubmit(async (values) => {
        await add(buildAddPayload(values));
        showToast.success("Added to the do-not-contact list");
        onClose();
    });

    const renderKindSelect = ({ field }: { field: { value: TAddFormValues["kind"]; onChange: (value: string) => void } }) => (
        <Select value={field.value} onValueChange={field.onChange}>
            <SelectTrigger id="dnc-kind" className="w-full">
                <SelectValue />
            </SelectTrigger>
            <SelectContent>
                <SelectItem value={DO_NOT_CONTACT_KIND.PHONE}>Phone number</SelectItem>
                <SelectItem value={DO_NOT_CONTACT_KIND.EMAIL}>Email address</SelectItem>
            </SelectContent>
        </Select>
    );

    return (
        <form onSubmit={onSubmit} noValidate className="space-y-4">
            <DialogHeader>
                <DialogTitle>Add to the do-not-contact list</DialogTitle>
                <DialogDescription>
                    Whoever owns this number or address disappears from Leads, and future runs won't add them again.
                </DialogDescription>
            </DialogHeader>

            <div className="space-y-1.5">
                <Label htmlFor="dnc-kind">Block a</Label>
                <Controller control={control} name="kind" render={renderKindSelect} />
            </div>

            <div className="space-y-1.5">
                <Label htmlFor="dnc-value">{isPhone ? "Phone number" : "Email address"}</Label>
                <Input
                    id="dnc-value"
                    inputMode={isPhone ? "tel" : "email"}
                    placeholder={isPhone ? "0300 1234567" : "name@company.pk"}
                    aria-invalid={!!errors.value}
                    {...register("value")}
                />
                {errors.value && <p className="text-sm text-destructive">{errors.value.message}</p>}
            </div>

            <div className="space-y-1.5">
                <Label htmlFor="dnc-reason">Reason (optional)</Label>
                <Textarea id="dnc-reason" rows={2} maxLength={REASON_MAX_LENGTH} {...register("reason")} />
            </div>

            <DialogFooter>
                <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
                    Cancel
                </Button>
                <Button type="submit" disabled={isPending}>
                    {isPending && <Loader2 className="animate-spin" />}
                    Add
                </Button>
            </DialogFooter>
        </form>
    );
};

export default AddDoNotContactForm;
