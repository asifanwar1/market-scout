import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useAddDoNotContact } from "@/hooks/api/compliance.queries";
import { showToast } from "@/lib/toast";

const schema = z
    .object({
        kind: z.enum(["phone", "email"]),
        value: z.string().trim().min(1, "Enter a phone number or email address"),
        reason: z.string().max(500, "At most 500 characters"),
    })
    .superRefine((values, ctx) => {
        if (values.kind === "email" && !z.email().safeParse(values.value).success) {
            ctx.addIssue({ code: "custom", path: ["value"], message: "Enter a valid email address" });
        }
    });

type TFormValues = z.infer<typeof schema>;

type TAddDoNotContactDialogProps = {
    open: boolean;
    onClose: () => void;
};

const AddDoNotContactDialog = ({ open, onClose }: TAddDoNotContactDialogProps) => {
    "use no memo"; // React Hook Form + React Compiler: see README

    const { mutateAsync: add, isPending } = useAddDoNotContact();
    const {
        register,
        control,
        handleSubmit,
        reset,
        formState: { errors },
    } = useForm<TFormValues>({
        resolver: zodResolver(schema),
        defaultValues: { kind: "phone", value: "", reason: "" },
    });
    const kind = useWatch({ control, name: "kind" });

    const close = () => {
        reset();
        onClose();
    };

    const onSubmit = handleSubmit(async (values) => {
        await add({
            ...(values.kind === "phone" ? { phone: values.value } : { email: values.value }),
            reason: values.reason.trim() || null,
        });
        showToast.success("Added to the do-not-contact list");
        close();
    });

    return (
        <Dialog open={open} onOpenChange={(next) => !next && !isPending && close()}>
            <DialogContent>
                <form onSubmit={onSubmit} noValidate className="space-y-4">
                    <DialogHeader>
                        <DialogTitle>Add to the do-not-contact list</DialogTitle>
                        <DialogDescription>
                            Whoever owns this number or address disappears from Leads, and future runs won't add them again.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-1.5">
                        <Label htmlFor="dnc-kind">Block a</Label>
                        <Controller
                            control={control}
                            name="kind"
                            render={({ field }) => (
                                <Select value={field.value} onValueChange={field.onChange}>
                                    <SelectTrigger id="dnc-kind" className="w-full">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="phone">Phone number</SelectItem>
                                        <SelectItem value="email">Email address</SelectItem>
                                    </SelectContent>
                                </Select>
                            )}
                        />
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="dnc-value">{kind === "phone" ? "Phone number" : "Email address"}</Label>
                        <Input
                            id="dnc-value"
                            inputMode={kind === "phone" ? "tel" : "email"}
                            placeholder={kind === "phone" ? "0300 1234567" : "name@company.pk"}
                            aria-invalid={!!errors.value}
                            {...register("value")}
                        />
                        {errors.value && <p className="text-sm text-destructive">{errors.value.message}</p>}
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="dnc-reason">Reason (optional)</Label>
                        <Textarea id="dnc-reason" rows={2} maxLength={500} {...register("reason")} />
                    </div>

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={close} disabled={isPending}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isPending}>
                            {isPending && <Loader2 className="animate-spin" />}
                            Add
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};

export default AddDoNotContactDialog;
