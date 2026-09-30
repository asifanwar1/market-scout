import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useParams } from "react-router-dom";

import { useGetProfile } from "@/hooks/api/catalog.queries";
import { useCreateProfile, useDeleteProfile, useUpdateProfile } from "@/hooks/api/profiles.queries";
import { useLeaveGuard } from "@/hooks/useLeaveGuard";
import { showToast } from "@/lib/toast";
import { APP_ROUTES } from "@/routes/appRoutes";
import {
    emptyProfile,
    profileSchema,
    toFormValues,
    toRequestBody,
    type TProfileFormValues,
} from "./profileForm";

export const useProfileEditor = () => {
    "use no memo"; // React Hook Form + React Compiler: see README

    const { id } = useParams();
    const navigate = useNavigate();
    const isNew = id === undefined;
    const profileId = isNew ? undefined : Number(id);

    const { data: profile, isPending: isLoadingProfile, isError } = useGetProfile(profileId);
    const { mutateAsync: createProfile, isPending: isCreating } = useCreateProfile();
    const { mutateAsync: updateProfile, isPending: isUpdating } = useUpdateProfile();
    const { mutateAsync: deleteProfile, isPending: isDeleting } = useDeleteProfile();

    const form = useForm<TProfileFormValues>({
        resolver: zodResolver(profileSchema),
        defaultValues: emptyProfile(),
    });
    const { isDirty } = form.formState;
    const { blocker, allowNextNavigation } = useLeaveGuard(isDirty);

    // Load the saved profile into the form. An edit in progress is never overwritten by a
    // background refetch.
    const { reset } = form;
    useEffect(() => {
        if (profile && !form.formState.isDirty) reset(toFormValues(profile));
        // eslint-disable-next-line react-hooks/exhaustive-deps -- reload only when the saved version changes
    }, [profile?.id, profile?.updated_at, reset]);

    const leaveTo = (path: string) => {
        allowNextNavigation();
        navigate(path);
    };

    const onSubmit = form.handleSubmit(
        async (values) => {
            const body = toRequestBody(values);
            if (isNew) {
                const created = await createProfile(body);
                // Adopt what the server saved (ids included) so nothing is left "unsaved".
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

    const [showDelete, setShowDelete] = useState(false);
    const handleDelete = async () => {
        await deleteProfile(profileId as number);
        showToast.success("Profile deleted");
        setShowDelete(false);
        leaveTo(APP_ROUTES.PROFILES);
    };

    return {
        form,
        isNew,
        profile,
        isLoading: !isNew && isLoadingProfile,
        isError: !isNew && isError,
        isDirty,
        onSubmit,
        isSaving: isCreating || isUpdating,
        discard: () => reset(profile ? toFormValues(profile) : emptyProfile()),
        showDelete,
        setShowDelete,
        handleDelete,
        isDeleting,
        blocker,
    };
};
