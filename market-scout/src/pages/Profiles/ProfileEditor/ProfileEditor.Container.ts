"use no memo";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useParams } from "react-router-dom";

import type { TProfileDetail } from "@/api/services/profiles/profiles.response.types";
import { useGetProfile } from "@/hooks/api/catalog.queries";
import { useCreateProfile, useDeleteProfile, useUpdateProfile } from "@/hooks/api/profiles.queries";
import { useLeaveGuard } from "@/hooks/useLeaveGuard";
import { showToast } from "@/lib/toast";
import { APP_ROUTES } from "@/routes/appRoutes";
import { emptyProfile, profileSchema, toFormValues, toRequestBody, type TProfileFormValues } from "./profileForm";
import { NEW_PROFILE_KEY, PROFILE_ID_PARAM } from "./ProfileEditor.constants";

const BLOCKED_STATE = "blocked";

export const useProfileEditorPage = () => {
    const params = useParams();
    const routeId = params[PROFILE_ID_PARAM];
    const isNew = routeId === undefined;
    const profileId = isNew ? undefined : Number(routeId);

    const { data: profile, isPending, isError: isLoadError } = useGetProfile(profileId);
    const isLoading = !isNew && isPending;
    const hasError = !isNew && isLoadError;
    const formKey = isNew ? NEW_PROFILE_KEY : `${routeId}-${profile?.updated_at ?? ""}`;

    return {
        isNew,
        profile,
        isLoading,
        hasError,
        formKey,
    };
};

export const useProfileEditor = (profile: TProfileDetail | undefined, isNew: boolean) => {
    const navigate = useNavigate();
    const profileId = profile?.id;

    const { mutateAsync: createProfile, isPending: isCreating } = useCreateProfile();
    const { mutateAsync: updateProfile, isPending: isUpdating } = useUpdateProfile();
    const { mutateAsync: deleteProfile, isPending: isDeleting } = useDeleteProfile();

    const form = useForm<TProfileFormValues>({
        resolver: zodResolver(profileSchema),
        defaultValues: profile ? toFormValues(profile) : emptyProfile(),
    });
    const { reset } = form;
    const { isDirty } = form.formState;
    const { blocker, allowNextNavigation } = useLeaveGuard(isDirty);

    const [isDeleteOpen, setIsDeleteOpen] = useState(false);

    const isSaving = isCreating || isUpdating;
    const isLeaveBlocked = blocker.state === BLOCKED_STATE;
    const pageTitle = isNew ? "New profile" : (profile?.name ?? "Profile");
    const deleteTitle = `Delete ${profile?.name ?? "this profile"}?`;
    const isDiscardDisabled = !isDirty || isSaving;
    const isSubmitDisabled = isSaving || (!isNew && !isDirty);
    const submitLabel = isNew ? "Create profile" : "Save changes";

    const leaveTo = (path: string) => {
        allowNextNavigation();
        navigate(path);
    };

    const onSubmit = form.handleSubmit(
        async (values) => {
            const body = toRequestBody(values);
            if (isNew) {
                const created = await createProfile(body);
                reset(toFormValues(created));
                showToast.success(`${created.name} created`);
                leaveTo(APP_ROUTES.PROFILES_DETAILS.replace(":id", String(created.id)));
                return;
            }
            const saved = await updateProfile({ id: profileId as number, body });
            reset(toFormValues(saved));
            showToast.success("Profile saved");
        },
        () => showToast.error("Some fields need fixing before this can be saved"),
    );

    const discard = () => {
        reset(profile ? toFormValues(profile) : emptyProfile());
    };

    const openDelete = () => {
        setIsDeleteOpen(true);
    };

    const closeDelete = () => {
        setIsDeleteOpen(false);
    };

    const confirmDelete = async () => {
        await deleteProfile(profileId as number);
        showToast.success("Profile deleted");
        setIsDeleteOpen(false);
        leaveTo(APP_ROUTES.PROFILES);
    };

    const confirmLeave = () => {
        if (blocker.state === BLOCKED_STATE) blocker.proceed();
    };

    const cancelLeave = () => {
        if (blocker.state === BLOCKED_STATE) blocker.reset();
    };

    return {
        form,
        isNew,
        isDirty,
        isSaving,
        isDeleting,
        isDeleteOpen,
        isLeaveBlocked,
        isDiscardDisabled,
        isSubmitDisabled,
        pageTitle,
        deleteTitle,
        submitLabel,
        onSubmit,
        discard,
        openDelete,
        closeDelete,
        confirmDelete,
        confirmLeave,
        cancelLeave,
    };
};
