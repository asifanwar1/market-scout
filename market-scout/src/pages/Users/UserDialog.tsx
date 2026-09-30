import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import type { UserModel } from "@/api/models/user.model";
import type { TUpdateUserBody } from "@/api/services/users/users.request.types";
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
import { Switch } from "@/components/ui/switch";
import { USER_ROLE } from "@/constants";
import { useCreateUser, useUpdateUser } from "@/hooks/api/users.queries";
import { showToast } from "@/lib/toast";
import { useStore } from "@/store";

// Same rules as the server, so mistakes show up next to the field.
const passwordRule = z
    .string()
    .min(8, "At least 8 characters")
    .max(128, "At most 128 characters")
    .refine((value) => /[A-Z]/.test(value), "Include an uppercase letter")
    .refine((value) => /\d/.test(value), "Include a digit")
    .refine((value) => /[!@#$%^&*()\-_=+[\]{}|;:,.<>?]/.test(value), "Include a special character such as ! or #");

const baseFields = {
    full_name: z.string().trim().min(2, "At least 2 characters").max(100, "At most 100 characters"),
    role: z.enum([USER_ROLE.ADMIN, USER_ROLE.SALES]),
    is_active: z.boolean(),
};

const createSchema = z.object({
    ...baseFields,
    email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
    password: passwordRule,
});

const editSchema = z.object({
    ...baseFields,
    email: z.string(),
    // Blank keeps the current password.
    password: z.string().refine((value) => value === "" || passwordRule.safeParse(value).success, {
        message: "At least 8 characters with an uppercase letter, a digit and a special character",
    }),
});

type TFormValues = z.infer<typeof createSchema>;

type TUserDialogProps = {
    open: boolean;
    // null when creating
    user: UserModel | null;
    onClose: () => void;
};

const EMPTY: TFormValues = { email: "", full_name: "", role: "sales", is_active: true, password: "" };

const UserDialog = ({ open, user, onClose }: TUserDialogProps) => {
    "use no memo"; // React Hook Form + React Compiler: see README

    const isEdit = user !== null;
    const currentUserId = useStore((state) => state.user?.id);
    const isSelf = isEdit && user.id === currentUserId;

    const { mutateAsync: createUser, isPending: isCreating } = useCreateUser();
    const { mutateAsync: updateUser, isPending: isUpdating } = useUpdateUser();
    const isPending = isCreating || isUpdating;

    const {
        register,
        control,
        handleSubmit,
        reset,
        formState: { errors },
    } = useForm<TFormValues>({
        resolver: zodResolver(isEdit ? editSchema : createSchema),
        defaultValues: EMPTY,
    });

    useEffect(() => {
        if (open) {
            reset(
                user
                    ? { email: user.email, full_name: user.full_name, role: user.role, is_active: user.is_active, password: "" }
                    : EMPTY,
            );
        }
    }, [open, user, reset]);

    const onSubmit = handleSubmit(async (values) => {
        if (!isEdit) {
            await createUser({
                email: values.email,
                full_name: values.full_name,
                role: values.role,
                password: values.password,
            });
            showToast.success(`${values.full_name} can now sign in`);
            onClose();
            return;
        }

        const changes: TUpdateUserBody = {};
        if (values.full_name !== user.full_name) changes.full_name = values.full_name;
        if (values.role !== user.role) changes.role = values.role;
        if (values.is_active !== user.is_active) changes.is_active = values.is_active;
        if (values.password) changes.password = values.password;

        if (Object.keys(changes).length === 0) {
            onClose();
            return;
        }
        await updateUser({ id: user.id, body: changes });
        showToast.success(
            changes.role || changes.is_active !== undefined || changes.password
                ? `${values.full_name} updated and signed out everywhere`
                : `${values.full_name} updated`,
        );
        onClose();
    });

    return (
        <Dialog open={open} onOpenChange={(next) => !next && !isPending && onClose()}>
            <DialogContent>
                <form onSubmit={onSubmit} noValidate className="space-y-4">
                    <DialogHeader>
                        <DialogTitle>{isEdit ? "Edit user" : "New user"}</DialogTitle>
                        <DialogDescription>
                            {isEdit
                                ? "Changing the role, switching the account off or setting a new password signs that person out everywhere."
                                : "They sign in with this email and password."}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-1.5">
                        <Label htmlFor="user-name">Full name</Label>
                        <Input id="user-name" aria-invalid={!!errors.full_name} {...register("full_name")} />
                        {errors.full_name && <p className="text-sm text-destructive">{errors.full_name.message}</p>}
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="user-email">Email</Label>
                        <Input
                            id="user-email"
                            type="email"
                            autoComplete="off"
                            disabled={isEdit}
                            aria-invalid={!!errors.email}
                            {...register("email")}
                        />
                        {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="user-role">Role</Label>
                        <Controller
                            control={control}
                            name="role"
                            render={({ field }) => (
                                <Select value={field.value} onValueChange={field.onChange} disabled={isSelf}>
                                    <SelectTrigger id="user-role" className="w-full">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value={USER_ROLE.SALES}>Sales: works the leads</SelectItem>
                                        <SelectItem value={USER_ROLE.ADMIN}>Admin: everything, including runs and settings</SelectItem>
                                    </SelectContent>
                                </Select>
                            )}
                        />
                        {isSelf && (
                            <p className="text-xs text-muted-foreground">You can't change your own role.</p>
                        )}
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="user-password">{isEdit ? "New password" : "Password"}</Label>
                        <Input
                            id="user-password"
                            type="password"
                            autoComplete="new-password"
                            placeholder={isEdit ? "Leave blank to keep the current one" : undefined}
                            aria-invalid={!!errors.password}
                            {...register("password")}
                        />
                        {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
                    </div>

                    {isEdit && (
                        <div className="flex items-center justify-between gap-4 rounded-lg border p-3">
                            <div>
                                <Label htmlFor="user-active">Account active</Label>
                                <p className="text-xs text-muted-foreground">
                                    {isSelf ? "You can't switch off your own account." : "Switched off accounts can't sign in."}
                                </p>
                            </div>
                            <Controller
                                control={control}
                                name="is_active"
                                render={({ field }) => (
                                    <Switch
                                        id="user-active"
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                        disabled={isSelf}
                                    />
                                )}
                            />
                        </div>
                    )}

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isPending}>
                            {isPending && <Loader2 className="animate-spin" />}
                            {isEdit ? "Save changes" : "Create user"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};

export default UserDialog;
