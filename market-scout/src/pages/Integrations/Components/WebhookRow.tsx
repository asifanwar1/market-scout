import { History, KeyRound, Pencil, Send, Trash2 } from "lucide-react";

import type { TWebhook } from "@/api/services/webhooks/webhooks.response.types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { WEBHOOK_EVENT_LABELS, type WebhookEvent } from "@/constants/integration.constants";
import { formatRelative } from "@/utils/format.utils";

type TWebhookRowProps = {
    hook: TWebhook;
    onToggle: (hook: TWebhook) => void;
    onTest: (hook: TWebhook) => void;
    onViewDeliveries: (hook: TWebhook) => void;
    onEdit: (hook: TWebhook) => void;
    onRotate: (hook: TWebhook) => void;
    onDelete: (hook: TWebhook) => void;
};

const WebhookRow = ({ hook, onToggle, onTest, onViewDeliveries, onEdit, onRotate, onDelete }: TWebhookRowProps) => {
    const renderEvent = (event: WebhookEvent) => (
        <Badge key={event} variant="secondary" className="font-normal">
            {WEBHOOK_EVENT_LABELS[event]}
        </Badge>
    );

    return (
        <li className="space-y-2 px-4 py-3">
            <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1 space-y-1">
                    <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                        {hook.name}
                        {!hook.is_active && <Badge variant="secondary">Off</Badge>}
                    </p>
                    <p className="break-all text-xs text-muted-foreground">{hook.url}</p>
                </div>
                <Switch checked={hook.is_active} aria-label={`${hook.name} is on`} onCheckedChange={() => onToggle(hook)} />
            </div>
            <div className="flex flex-wrap gap-1.5">{hook.events.map(renderEvent)}</div>
            <p className="text-xs text-muted-foreground">
                {hook.last_delivery_at ? `Last call ${formatRelative(hook.last_delivery_at)}` : "Not called yet"}
                {hook.last_status_code !== null && ` · answered ${hook.last_status_code}`}
                {" · "}secret {hook.secret_hint}
            </p>
            {hook.last_error && <p className="text-xs text-destructive">{hook.last_error}</p>}
            <div className="flex flex-wrap gap-1.5">
                <Button variant="outline" size="xs" onClick={() => onTest(hook)}>
                    <Send />
                    Test
                </Button>
                <Button variant="outline" size="xs" onClick={() => onViewDeliveries(hook)}>
                    <History />
                    Deliveries
                </Button>
                <Button variant="outline" size="xs" onClick={() => onEdit(hook)}>
                    <Pencil />
                    Edit
                </Button>
                <Button variant="outline" size="xs" onClick={() => onRotate(hook)}>
                    <KeyRound />
                    New secret
                </Button>
                <Button variant="outline" size="xs" aria-label={`Delete ${hook.name}`} onClick={() => onDelete(hook)}>
                    <Trash2 />
                    Delete
                </Button>
            </div>
        </li>
    );
};

export default WebhookRow;
