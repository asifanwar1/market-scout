import { Loader2 } from "lucide-react";
import { useState } from "react";

import type { TEventInfo, TWebhook } from "@/api/services/webhooks/webhooks.response.types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { WEBHOOK_NAME_MAX_LENGTH, WEBHOOK_URL_MAX_LENGTH, type WebhookEvent } from "@/constants/integration.constants";
import { useCreateWebhook, useGetWebhookConfig, useUpdateWebhook } from "@/hooks/api/integrations.queries";
import { showToast } from "@/lib/toast";
import { WEBHOOK_URL_HELP, WEBHOOK_URL_HELP_PRIVATE, WEBHOOK_URL_PLACEHOLDER } from "../Integrations.constants";

const NAME_PLACEHOLDER = "e.g. Billing app";

type TWebhookDialogProps = {
    open: boolean;
    hook: TWebhook | null;
    onClose: () => void;
    onCreated: (secret: string) => void;
};

const WebhookForm = ({ hook, onClose, onCreated }: Omit<TWebhookDialogProps, "open">) => {
    const { data: config } = useGetWebhookConfig();
    const { mutateAsync: create, isPending: isCreating } = useCreateWebhook();
    const { mutateAsync: update, isPending: isUpdating } = useUpdateWebhook();

    const [name, setName] = useState(hook?.name ?? "");
    const [url, setUrl] = useState(hook?.url ?? "");
    const [events, setEvents] = useState<WebhookEvent[]>(hook?.events ?? []);

    const available = config?.events ?? [];
    const isSaving = isCreating || isUpdating;
    const canSave = name.trim().length > 0 && url.trim().length > 0 && events.length > 0 && !isSaving;
    const urlHelp = config?.allow_private_urls ? WEBHOOK_URL_HELP_PRIVATE : WEBHOOK_URL_HELP;

    const toggleEvent = (key: WebhookEvent, checked: boolean) => {
        setEvents(checked ? [...events, key] : events.filter((event) => event !== key));
    };

    const save = async () => {
        const body = { name: name.trim(), url: url.trim(), events };
        if (hook) {
            await update({ id: hook.id, body });
            showToast.success("Webhook saved");
            onClose();
            return;
        }
        const created = await create(body);
        onCreated(created.secret);
    };

    const renderEvent = (info: TEventInfo) => (
        <div key={info.key} className="flex items-start gap-2">
            <Checkbox
                id={`event-${info.key}`}
                checked={events.includes(info.key)}
                onCheckedChange={(checked) => toggleEvent(info.key, checked === true)}
            />
            <div className="space-y-0.5">
                <Label htmlFor={`event-${info.key}`}>{info.label}</Label>
                <p className="text-xs text-muted-foreground">{info.description}</p>
            </div>
        </div>
    );

    return (
        <DialogContent className="sm:max-w-xl">
            <DialogHeader>
                <DialogTitle>{hook ? "Edit webhook" : "New webhook"}</DialogTitle>
                <DialogDescription>Choose where to send calls and which events to send.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
                <div className="space-y-1.5">
                    <Label htmlFor="hook-name">Name</Label>
                    <Input
                        id="hook-name"
                        maxLength={WEBHOOK_NAME_MAX_LENGTH}
                        value={name}
                        placeholder={NAME_PLACEHOLDER}
                        onChange={(event) => setName(event.target.value)}
                    />
                </div>
                <div className="space-y-1.5">
                    <Label htmlFor="hook-url">Address</Label>
                    <Input
                        id="hook-url"
                        maxLength={WEBHOOK_URL_MAX_LENGTH}
                        value={url}
                        placeholder={WEBHOOK_URL_PLACEHOLDER}
                        onChange={(event) => setUrl(event.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">{urlHelp}</p>
                </div>
                <div className="space-y-3">
                    <Label>Send me</Label>
                    {available.map(renderEvent)}
                </div>
            </div>
            <DialogFooter>
                <Button variant="ghost" onClick={onClose}>
                    Cancel
                </Button>
                <Button disabled={!canSave} onClick={save}>
                    {isSaving && <Loader2 className="animate-spin" />}
                    {hook ? "Save webhook" : "Create webhook"}
                </Button>
            </DialogFooter>
        </DialogContent>
    );
};

const WebhookDialog = ({ open, hook, onClose, onCreated }: TWebhookDialogProps) => {
    const onOpenChange = (next: boolean) => {
        if (!next) onClose();
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            {open && <WebhookForm key={hook?.id ?? "new"} hook={hook} onClose={onClose} onCreated={onCreated} />}
        </Dialog>
    );
};

export default WebhookDialog;
