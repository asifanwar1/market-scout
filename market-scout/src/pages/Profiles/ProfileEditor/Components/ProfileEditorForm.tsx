"use no memo";

import { ArrowLeft, Loader2, Trash2 } from "lucide-react";
import { FormProvider } from "react-hook-form";
import { Link } from "react-router-dom";

import type { TProfileDetail } from "@/api/services/profiles/profiles.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import PageHeader from "@/components/custom/PageHeader";
import { Button } from "@/components/ui/button";
import { APP_ROUTES } from "@/routes/appRoutes";
import { DELETE_PROFILE_DESCRIPTION, LEAVE_DESCRIPTION, PROFILE_EDITOR_DESCRIPTION } from "../ProfileEditor.constants";
import { useProfileEditor } from "../ProfileEditor.Container";
import BasicsSection from "./BasicsSection";
import ScoringSection from "./ScoringSection";
import SearchTermsSection from "./SearchTermsSection";
import SegmentsSection from "./SegmentsSection";

type TProfileEditorFormProps = {
    profile: TProfileDetail | undefined;
    isNew: boolean;
};

const ProfileEditorForm = ({ profile, isNew }: TProfileEditorFormProps) => {
    const {
        form,
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
    } = useProfileEditor(profile, isNew);

    return (
        <FormProvider {...form}>
            <form onSubmit={onSubmit} noValidate className="max-w-5xl space-y-6">
                <Button asChild variant="ghost" size="sm" className="-ml-2">
                    <Link to={APP_ROUTES.PROFILES}>
                        <ArrowLeft />
                        All profiles
                    </Link>
                </Button>

                <PageHeader title={pageTitle} description={PROFILE_EDITOR_DESCRIPTION} />

                <BasicsSection />
                <SegmentsSection />
                <SearchTermsSection />
                <ScoringSection />

                <div className="sticky bottom-0 -mx-4 flex flex-wrap items-center justify-between gap-3 border-t bg-background/95 px-4 py-3 backdrop-blur md:-mx-6 md:px-6">
                    <div className="flex items-center gap-3">
                        {!isNew && (
                            <Button type="button" variant="ghost" onClick={openDelete}>
                                <Trash2 />
                                Delete profile
                            </Button>
                        )}
                        {isDirty && <span className="text-sm text-muted-foreground">Unsaved changes</span>}
                    </div>
                    <div className="flex items-center gap-2">
                        <Button type="button" variant="outline" disabled={isDiscardDisabled} onClick={discard}>
                            Discard changes
                        </Button>
                        <Button type="submit" disabled={isSubmitDisabled}>
                            {isSaving && <Loader2 className="animate-spin" />}
                            {submitLabel}
                        </Button>
                    </div>
                </div>
            </form>

            <ConfirmationModal
                open={isDeleteOpen}
                destructive
                title={deleteTitle}
                description={DELETE_PROFILE_DESCRIPTION}
                confirmText="Delete profile"
                isLoading={isDeleting}
                onConfirm={confirmDelete}
                onClose={closeDelete}
            />

            <ConfirmationModal
                open={isLeaveBlocked}
                title="Discard your changes?"
                description={LEAVE_DESCRIPTION}
                confirmText="Discard and leave"
                cancelText="Keep editing"
                onConfirm={confirmLeave}
                onClose={cancelLeave}
            />
        </FormProvider>
    );
};

export default ProfileEditorForm;
