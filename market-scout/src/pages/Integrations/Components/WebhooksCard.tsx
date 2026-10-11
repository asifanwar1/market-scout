import { Loader2, Plus, Webhook as WebhookIcon } from "lucide-react";
import { useState } from "react";

import type { TWebhook } from "@/api/services/webhooks/webhooks.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    useDeleteWebhook,
    useGetWebhooks,
    useRotateWebhookSecret,
    useSendWebhookTest,
    useUpdateWebhook,
} from "@/hooks/api/integrations.queries";
import { showToast } from "@/lib/toast";
import {
    SECRET_CREATED_DESCRIPTION,
    SECRET_CREATED_TITLE,
    WEBHOOK_DELETE_DESCRIPTION,
    WEBHOOK_DELETE_TITLE,
    WEBHOOK_ROTATE_DESCRIPTION,
    WEBHOOK_ROTATE_TITLE,
    WEBHOOKS_DESCRIPTION,
    WEBHOOKS_EMPTY,
    WEBHOOKS_TITLE,
} from "../Integrations.constants";
import DeliveriesDialog from "./DeliveriesDialog";
import ShownOnceDialog from "./ShownOnceDialog";
import WebhookDialog from "./WebhookDialog";
import WebhookRow from "./WebhookRow";

const WebhooksCard = () => {
    const { data, isPending } = useGetWebhooks();
    const { mutateAsync: update } = useUpdateWebhook();
    const { mutateAsync: remove, isPending: isDeleting } = useDeleteWebhook();
    const { mutateAsync: rotate, isPending: isRotating } = useRotateWebhookSecret();
    const { mutateAsync: sendTest, isPending: isTesting } = useSendWebhookTest();

    const [isCreating, setIsCreating] = useState(false);
    const [editing, setEditing] = useState<TWebhook | null>(null);
    const [deleting, setDeleting] = useState<TWebhook | null>(null);
    const [rotating, setRotating] = useState<TWebhook | null>(null);
    const [viewingId, setViewingId] = useState<number | null>(null);
    const [secret, setSecret] = useState<string | null>(null);

    const hooks = data?.data ?? [];
    const dialogOpen = isCreating || editing !== null;

    const closeDialog = () => {
        setIsCreating(false);
        setEditing(null);
    };

    const onCreated = (value: string) => {
        closeDialog();
        setSecret(value);
    };

    const toggleActive = async (hook: TWebhook) => {
        await update({ id: hook.id, body: { is_active: !hook.is_active } });
        showToast.success(hook.is_active ? "Webhook switched off" : "Webhook switched on");
    };

    const test = async (hook: TWebhook) => {
        await sendTest(hook.id);
        setViewingId(hook.id);
    };

    const confirmDelete = async () => {
        if (deleting === null) return;
        await remove(deleting.id);
        setDeleting(null);
        showToast.success("Webhook deleted");
    };

    const confirmRotate = async () => {
        if (rotating === null) return;
        const rotated = await rotate(rotating.id);
        setRotating(null);
        setSecret(rotated.secret);
    };

    const renderHook = (hook: TWebhook) => (
        <WebhookRow
            key={hook.id}
            hook={hook}
            onToggle={toggleActive}
            onTest={test}
            onViewDeliveries={(item) => setViewingId(item.id)}
            onEdit={setEditing}
            onRotate={setRotating}
            onDelete={setDeleting}
        />
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle>{WEBHOOKS_TITLE}</CardTitle>
                <CardDescription>{WEBHOOKS_DESCRIPTION}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <Button onClick={() => setIsCreating(true)}>
                    <Plus />
                    New webhook
                </Button>
                {isTesting && (
                    <p className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="size-4 animate-spin" />
                        Sending a test…
                    </p>
                )}
                {isPending ? (
                    <Loading />
                ) : hooks.length > 0 ? (
                    <ul className="divide-y rounded-md border">{hooks.map(renderHook)}</ul>
                ) : (
                    <EmptyState icon={WebhookIcon} title={WEBHOOKS_EMPTY} />
                )}
            </CardContent>

            <WebhookDialog open={dialogOpen} hook={editing} onClose={closeDialog} onCreated={onCreated} />
            <DeliveriesDialog webhookId={viewingId} onClose={() => setViewingId(null)} />
            <ShownOnceDialog
                value={secret}
                title={SECRET_CREATED_TITLE}
                description={SECRET_CREATED_DESCRIPTION}
                label="signing secret"
                onClose={() => setSecret(null)}
            />
            <ConfirmationModal
                open={deleting !== null}
                destructive
                title={WEBHOOK_DELETE_TITLE}
                description={WEBHOOK_DELETE_DESCRIPTION}
                confirmText="Delete"
                isLoading={isDeleting}
                onConfirm={confirmDelete}
                onClose={() => setDeleting(null)}
            />
            <ConfirmationModal
                open={rotating !== null}
                title={WEBHOOK_ROTATE_TITLE}
                description={WEBHOOK_ROTATE_DESCRIPTION}
                confirmText="Make new secret"
                isLoading={isRotating}
                onConfirm={confirmRotate}
                onClose={() => setRotating(null)}
            />
        </Card>
    );
};

export default WebhooksCard;
