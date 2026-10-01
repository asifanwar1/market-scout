import { Link } from "react-router-dom";

import Loading from "@/components/custom/Loading";
import { Button } from "@/components/ui/button";
import { APP_ROUTES } from "@/routes/appRoutes";
import ProfileEditorForm from "./Components/ProfileEditorForm";
import { useProfileEditorPage } from "./ProfileEditor.Container";

const ProfileEditor = () => {
    const { isNew, profile, isLoading, hasError, formKey } = useProfileEditorPage();

    if (isLoading) return <Loading />;

    if (hasError) {
        return (
            <div className="space-y-4">
                <p className="text-sm text-muted-foreground">This profile couldn't be found.</p>
                <Button asChild variant="outline">
                    <Link to={APP_ROUTES.PROFILES}>Back to profiles</Link>
                </Button>
            </div>
        );
    }

    return <ProfileEditorForm key={formKey} profile={profile} isNew={isNew} />;
};

export default ProfileEditor;
