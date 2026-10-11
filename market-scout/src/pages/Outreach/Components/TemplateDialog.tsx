import { Loader2 } from "lucide-react";
import { useState } from "react";

import type { TMessageTemplate, TPlaceholder } from "@/api/services/outreach/outreach.response.types";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { TEMPLATE_CHANNEL, TEMPLATE_CHANNEL_OPTIONS, TEMPLATE_NAME_MAX_LENGTH, type TemplateChannel } from "@/constants/outreach.constants";
import { useCreateTemplate, useGetOutreachConfig, useUpdateTemplate } from "@/hooks/api/outreach.queries";
import { showToast } from "@/lib/toast";
import { appendPlaceholder, describePlaceholder, placeholderToken, supportsSubject } from "@/utils/outreach.utils";

const FALLBACK_SUBJECT_MAX = 200;
const FALLBACK_BODY_MAX = 2000;
const NAME_PLACEHOLDER = "e.g. First hello";
const BODY_PLACEHOLDER = "Hello {contact_name}, I noticed {business_name} in {city}…";

type TTemplateDialogProps = {
    open: boolean;
    template: TMessageTemplate | null;
    onClose: () => void;
};

type TTemplateFormProps = {
    template: TMessageTemplate | null;
    onClose: () => void;
};

const TemplateForm = ({ template, onClose }: TTemplateFormProps) => {
    const { data: config } = useGetOutreachConfig();
    const { mutateAsync: create, isPending: isCreating } = useCreateTemplate();
    const { mutateAsync: update, isPending: isUpdating } = useUpdateTemplate();

    const [name, setName] = useState(template?.name ?? "");
    const [channel, setChannel] = useState<TemplateChannel>(template?.channel ?? TEMPLATE_CHANNEL.WHATSAPP);
    const [subject, setSubject] = useState(template?.subject ?? "");
    const [body, setBody] = useState(template?.body ?? "");

    const placeholders = config?.placeholders ?? [];
    const subjectMax = config?.subject_max_length ?? FALLBACK_SUBJECT_MAX;
    const bodyMax = config?.body_max_length ?? FALLBACK_BODY_MAX;
    const showSubject = supportsSubject(channel);
    const isSaving = isCreating || isUpdating;
    const canSave = name.trim().length > 0 && body.trim().length > 0 && !isSaving;

    const onChannelChange = (value: string) => {
        const next = TEMPLATE_CHANNEL_OPTIONS.find((option) => option.value === value);
        if (next) setChannel(next.value);
    };

    const addToBody = (key: string) => {
        setBody(appendPlaceholder(body, key));
    };

    const save = async () => {
        const payload = { name: name.trim(), channel, subject: showSubject ? subject.trim() || null : null, body: body.trim() };
        if (template) {
            await update({ id: template.id, body: payload });
        } else {
            await create(payload);
        }
        showToast.success(template ? "Template saved" : "Template added");
        onClose();
    };

    const renderChannel = (option: (typeof TEMPLATE_CHANNEL_OPTIONS)[number]) => (
        <SelectItem key={option.value} value={option.value}>
            {option.label}
        </SelectItem>
    );

    const renderPlaceholder = (placeholder: TPlaceholder) => (
        <Button
            key={placeholder.key}
            type="button"
            variant="outline"
            size="xs"
            title={describePlaceholder(placeholder)}
            onClick={() => addToBody(placeholder.key)}
        >
            {placeholderToken(placeholder.key)}
        </Button>
    );

    return (
        <DialogContent className="sm:max-w-xl">
            <DialogHeader>
                <DialogTitle>{template ? "Edit template" : "New template"}</DialogTitle>
                <DialogDescription>
                    Use the buttons below to drop in details that change for each lead. Anything else is sent as written.
                </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="template-name">Name</Label>
                        <Input
                            id="template-name"
                            maxLength={TEMPLATE_NAME_MAX_LENGTH}
                            value={name}
                            placeholder={NAME_PLACEHOLDER}
                            onChange={(event) => setName(event.target.value)}
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="template-channel">For</Label>
                        <Select value={channel} onValueChange={onChannelChange}>
                            <SelectTrigger id="template-channel" className="w-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>{TEMPLATE_CHANNEL_OPTIONS.map(renderChannel)}</SelectContent>
                        </Select>
                    </div>
                </div>

                {showSubject && (
                    <div className="space-y-1.5">
                        <Label htmlFor="template-subject">Email subject</Label>
                        <Input
                            id="template-subject"
                            maxLength={subjectMax}
                            value={subject}
                            onChange={(event) => setSubject(event.target.value)}
                        />
                    </div>
                )}

                <div className="space-y-1.5">
                    <Label htmlFor="template-body">Message</Label>
                    <Textarea
                        id="template-body"
                        rows={7}
                        maxLength={bodyMax}
                        value={body}
                        placeholder={BODY_PLACEHOLDER}
                        onChange={(event) => setBody(event.target.value)}
                    />
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs text-muted-foreground">Insert:</span>
                        {placeholders.map(renderPlaceholder)}
                    </div>
                </div>
            </div>

            <DialogFooter>
                <Button variant="ghost" onClick={onClose}>
                    Cancel
                </Button>
                <Button disabled={!canSave} onClick={save}>
                    {isSaving && <Loader2 className="animate-spin" />}
                    Save template
                </Button>
            </DialogFooter>
        </DialogContent>
    );
};

const TemplateDialog = ({ open, template, onClose }: TTemplateDialogProps) => {
    const onOpenChange = (next: boolean) => {
        if (!next) onClose();
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            {open && <TemplateForm key={template?.id ?? "new"} template={template} onClose={onClose} />}
        </Dialog>
    );
};

export default TemplateDialog;
