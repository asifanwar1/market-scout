import { Pencil, Trash2 } from "lucide-react";

import type { TMessageTemplate } from "@/api/services/outreach/outreach.response.types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TEMPLATE_CHANNEL_LABELS } from "@/constants/outreach.constants";
import { previewText } from "@/utils/outreach.utils";

type TTemplateRowProps = {
    template: TMessageTemplate;
    isAdmin: boolean;
    onEdit: (template: TMessageTemplate) => void;
    onDelete: (template: TMessageTemplate) => void;
};

const TemplateRow = ({ template, isAdmin, onEdit, onDelete }: TTemplateRowProps) => {
    return (
        <li className="flex items-start gap-3 px-4 py-3">
            <div className="min-w-0 flex-1 space-y-1">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                    {template.name}
                    <Badge variant="secondary">{TEMPLATE_CHANNEL_LABELS[template.channel]}</Badge>
                </p>
                {template.subject && <p className="break-words text-xs text-muted-foreground">Subject: {template.subject}</p>}
                <p className="break-words text-sm text-muted-foreground">{previewText(template.body)}</p>
            </div>
            {isAdmin && (
                <>
                    <Button variant="ghost" size="icon-xs" aria-label={`Edit ${template.name}`} onClick={() => onEdit(template)}>
                        <Pencil />
                    </Button>
                    <Button variant="ghost" size="icon-xs" aria-label={`Delete ${template.name}`} onClick={() => onDelete(template)}>
                        <Trash2 />
                    </Button>
                </>
            )}
        </li>
    );
};

export default TemplateRow;
