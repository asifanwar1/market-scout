import { FileText, Plus } from "lucide-react";
import { useState } from "react";

import type { TMessageTemplate } from "@/api/services/outreach/outreach.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useDeleteTemplate, useGetTemplates } from "@/hooks/api/outreach.queries";
import { showToast } from "@/lib/toast";
import {
    DELETE_TEMPLATE_DESCRIPTION,
    DELETE_TEMPLATE_TITLE,
    TEMPLATES_DESCRIPTION,
    TEMPLATES_EMPTY_ADMIN,
    TEMPLATES_EMPTY_OTHER,
    TEMPLATES_EMPTY_TITLE,
    TEMPLATES_TITLE,
} from "../Outreach.constants";
import TemplateDialog from "./TemplateDialog";
import TemplateRow from "./TemplateRow";

type TTemplatesCardProps = {
    isAdmin: boolean;
};

const TemplatesCard = ({ isAdmin }: TTemplatesCardProps) => {
    const { data, isPending } = useGetTemplates();
    const { mutateAsync: removeTemplate, isPending: isDeleting } = useDeleteTemplate();
    const [isCreating, setIsCreating] = useState(false);
    const [editing, setEditing] = useState<TMessageTemplate | null>(null);
    const [deleting, setDeleting] = useState<TMessageTemplate | null>(null);

    const templates = data?.data ?? [];
    const dialogOpen = isCreating || editing !== null;

    const closeDialog = () => {
        setIsCreating(false);
        setEditing(null);
    };

    const confirmDelete = async () => {
        if (deleting === null) return;
        await removeTemplate(deleting.id);
        setDeleting(null);
        showToast.success("Template deleted");
    };

    const renderTemplate = (template: TMessageTemplate) => (
        <TemplateRow key={template.id} template={template} isAdmin={isAdmin} onEdit={setEditing} onDelete={setDeleting} />
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle>{TEMPLATES_TITLE}</CardTitle>
                <CardDescription>{TEMPLATES_DESCRIPTION}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {isAdmin && (
                    <Button onClick={() => setIsCreating(true)}>
                        <Plus />
                        New template
                    </Button>
                )}
                {isPending ? (
                    <Loading />
                ) : templates.length > 0 ? (
                    <ul className="divide-y rounded-md border">{templates.map(renderTemplate)}</ul>
                ) : (
                    <EmptyState
                        icon={FileText}
                        title={TEMPLATES_EMPTY_TITLE}
                        description={isAdmin ? TEMPLATES_EMPTY_ADMIN : TEMPLATES_EMPTY_OTHER}
                    />
                )}
            </CardContent>

            <TemplateDialog open={dialogOpen} template={editing} onClose={closeDialog} />

            <ConfirmationModal
                open={deleting !== null}
                destructive
                title={DELETE_TEMPLATE_TITLE}
                description={DELETE_TEMPLATE_DESCRIPTION}
                confirmText="Delete"
                isLoading={isDeleting}
                onConfirm={confirmDelete}
                onClose={() => setDeleting(null)}
            />
        </Card>
    );
};

export default TemplatesCard;
