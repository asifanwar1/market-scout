"use no memo";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { Controller, useForm } from "react-hook-form";

import type { UserModel } from "@/api/models/user.model";
import type { TCreateUserBody, TUpdateUserBody } from "@/api/services/users/users.request.types";
import { Button } from "@/components/ui/button";
import { DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { USER_ROLE } from "@/constants";
import { useCreateUser, useUpdateUser } from "@/hooks/api/users.queries";
import { showToast } from "@/lib/toast";
import { useStore } from "@/store";
import type { TUserFormValues } from "../Users.types";
import { createUserSchema, EMPTY_USER_FORM, editUserSchema } from "./UserDialog.schema";

type TUserFormProps = {
    user: UserModel | null;
    onClose: () => void;
};

const buildUserFormValues = (user: UserModel | null): TUserFormValues =>
    user
        ? { email: user.email, full_name: user.full_name, role: user.role, is_active: user.is_active, password: "" }
        : EMPTY_USER_FORM;

const buildCreateUserPayload = (values: TUserFormValues): TCreateUserBody => ({
    email: values.email,
    full_name: values.full_name,
    role: values.role,
    password: values.password,
});

const buildUpdateUserPayload = (values: TUserFormValues, user: UserModel): TUpdateUserBody => ({
    ...(values.full_name !== user.full_name && { full_name: values.full_name }),
    ...(values.role !== user.role && { role: values.role }),
    ...(values.is_active !== user.is_active && { is_active: values.is_active }),
    ...(values.password && { password: values.password }),
});

const UserForm = ({ user, onClose }: TUserFormProps) => {
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
        formState: { errors },
    } = useForm<TUserFormValues>({
        resolver: zodResolver(isEdit ? editUserSchema : createUserSchema),
        defaultValues: buildUserFormValues(user),
    });

    const onSubmit = handleSubmit(async (values) => {
        if (!isEdit) {
            await createUser(buildCreateUserPayload(values));
            showToast.success(`${values.full_name} can now sign in`);
            onClose();
            return;
        }

        const changes = buildUpdateUserPayload(values, user);
        if (Object.keys(changes).length === 0) {
            onClose();
            return;
        }
        await updateUser({ id: user.id, body: changes });
        const signsOut = changes.role || changes.is_active !== undefined || changes.password;
        showToast.success(signsOut ? `${values.full_name} updated and signed out everywhere` : `${values.full_name} updated`);
        onClose();
    });

    const renderRoleSelect = ({ field }: { field: { value: TUserFormValues["role"]; onChange: (value: string) => void } }) => (
        <Select value={field.value} onValueChange={field.onChange} disabled={isSelf}>
            <SelectTrigger id="user-role" className="w-full">
                <SelectValue />
            </SelectTrigger>
            <SelectContent>
                <SelectItem value={USER_ROLE.SALES}>Sales: works the leads</SelectItem>
                <SelectItem value={USER_ROLE.ADMIN}>Admin: everything, including runs and settings</SelectItem>
            </SelectContent>
        </Select>
    );

    const renderActiveSwitch = ({ field }: { field: { value: boolean; onChange: (value: boolean) => void } }) => (
        <Switch id="user-active" checked={field.value} onCheckedChange={field.onChange} disabled={isSelf} />
    );

    return (
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
                <Input id="user-email" type="email" autoComplete="off" disabled={isEdit} aria-invalid={!!errors.email} {...register("email")} />
                {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
            </div>

            <div className="space-y-1.5">
                <Label htmlFor="user-role">Role</Label>
                <Controller control={control} name="role" render={renderRoleSelect} />
                {isSelf && <p className="text-xs text-muted-foreground">You can't change your own role.</p>}
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
                    <Controller control={control} name="is_active" render={renderActiveSwitch} />
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
    );
};

export default UserForm;
