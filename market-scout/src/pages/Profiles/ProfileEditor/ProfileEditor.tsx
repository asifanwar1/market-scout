import { ArrowLeft, Loader2, Trash2 } from "lucide-react";
import { FormProvider } from "react-hook-form";
import { Link, useParams } from "react-router-dom";

import ConfirmationModal from "@/components/custom/ConfirmationModal";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import { Button } from "@/components/ui/button";
import { APP_ROUTES } from "@/routes/appRoutes";
import BasicsSection from "./BasicsSection";
import { useProfileEditor } from "./ProfileEditor.Container";
import ScoringSection from "./ScoringSection";
import SearchTermsSection from "./SearchTermsSection";
import SegmentsSection from "./SegmentsSection";

const ProfileEditorForm = () => {
    "use no memo"; // React Hook Form + React Compiler: see README

    const editor = useProfileEditor();
    const { form, isNew, profile, isDirty, blocker } = editor;

    if (editor.isLoading) return <Loading />;
    if (editor.isError) {
        return (
            <div className="space-y-4">
                <p className="text-sm text-muted-foreground">This profile couldn't be found.</p>
                <Button asChild variant="outline">
                    <Link to={APP_ROUTES.PROFILES}>Back to profiles</Link>
                </Button>
            </div>
        );
    }

    return (
        <FormProvider {...form}>
            <form onSubmit={editor.onSubmit} noValidate className="max-w-5xl space-y-6">
                <Button asChild variant="ghost" size="sm" className="-ml-2">
                    <Link to={APP_ROUTES.PROFILES}>
                        <ArrowLeft />
                        All profiles
                    </Link>
                </Button>

                <PageHeader
                    title={isNew ? "New profile" : (profile?.name ?? "Profile")}
                    description="Changes take effect the next time a run starts. Leads already found keep their segment and score until they're seen again."
                />

                <BasicsSection />
                <SegmentsSection />
                <SearchTermsSection />
                <ScoringSection />

                <div className="sticky bottom-0 -mx-4 flex flex-wrap items-center justify-between gap-3 border-t bg-background/95 px-4 py-3 backdrop-blur md:-mx-6 md:px-6">
                    <div className="flex items-center gap-3">
                        {!isNew && (
                            <Button type="button" variant="ghost" onClick={() => editor.setShowDelete(true)}>
                                <Trash2 />
                                Delete profile
                            </Button>
                        )}
                        {isDirty && <span className="text-sm text-muted-foreground">Unsaved changes</span>}
                    </div>
                    <div className="flex items-center gap-2">
                        <Button type="button" variant="outline" disabled={!isDirty || editor.isSaving} onClick={editor.discard}>
                            Discard changes
                        </Button>
                        <Button type="submit" disabled={editor.isSaving || (!isNew && !isDirty)}>
                            {editor.isSaving && <Loader2 className="animate-spin" />}
                            {isNew ? "Create profile" : "Save changes"}
                        </Button>
                    </div>
                </div>
            </form>

            <ConfirmationModal
                open={editor.showDelete}
                destructive
                title={`Delete ${profile?.name ?? "this profile"}?`}
                description="Its segments and search terms are deleted, and leads lose their classification under it. Past runs keep their history. Consider switching it off instead."
                confirmText="Delete profile"
                isLoading={editor.isDeleting}
                onConfirm={editor.handleDelete}
                onClose={() => editor.setShowDelete(false)}
            />

            <ConfirmationModal
                open={blocker.state === "blocked"}
                title="Discard your changes?"
                description="You have unsaved changes on this profile. Leaving now throws them away."
                confirmText="Discard and leave"
                cancelText="Keep editing"
                onConfirm={() => blocker.state === "blocked" && blocker.proceed()}
                onClose={() => blocker.state === "blocked" && blocker.reset()}
            />
        </FormProvider>
    );
};

// Keyed by the profile so moving from /profiles/new to the profile just created (or between
// profiles) starts from a clean form instead of carrying the previous one's unsaved state.
const ProfileEditor = () => {
    const { id } = useParams();
    return <ProfileEditorForm key={id ?? "new"} />;
};

export default ProfileEditor;
