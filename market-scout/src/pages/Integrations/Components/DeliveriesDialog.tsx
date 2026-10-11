import { Inbox, RotateCcw } from "lucide-react";
import { useState } from "react";

import type { TDelivery } from "@/api/services/webhooks/webhooks.response.types";
import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import Pagination from "@/components/custom/Pagination";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DELIVERY_STATUS, DELIVERY_STATUS_LABELS, WEBHOOK_EVENT_LABELS } from "@/constants/integration.constants";
import { FIRST_PAGE } from "@/constants";
import { useGetDeliveries, useRetryDelivery } from "@/hooks/api/integrations.queries";
import { showToast } from "@/lib/toast";
import { formatRelative, formatUpcoming } from "@/utils/format.utils";
import { DELIVERIES_EMPTY, DELIVERIES_PAGE_SIZE, DELIVERIES_TITLE } from "../Integrations.constants";

const STATUS_CLASSES: Record<string, string> = {
    [DELIVERY_STATUS.DELIVERED]: "bg-success text-success-foreground",
    [DELIVERY_STATUS.FAILED]: "bg-destructive/10 text-destructive",
    [DELIVERY_STATUS.QUEUED]: "bg-warning text-warning-foreground",
    [DELIVERY_STATUS.RUNNING]: "bg-warning text-warning-foreground",
};

type TDeliveriesDialogProps = {
    webhookId: number | null;
    onClose: () => void;
};

const DeliveriesList = ({ webhookId }: { webhookId: number }) => {
    const [page, setPage] = useState(FIRST_PAGE);
    const { data, isPending } = useGetDeliveries(webhookId, { page, limit: DELIVERIES_PAGE_SIZE });
    const { mutateAsync: retry, isPending: isRetrying } = useRetryDelivery();

    const rows = data?.data ?? [];
    const total = data?.count ?? 0;

    const retryDelivery = async (delivery: TDelivery) => {
        await retry(delivery.id);
        showToast.success("Queued to send again");
    };

    const renderDelivery = (delivery: TDelivery) => (
        <li key={delivery.id} className="flex items-start gap-3 px-4 py-3">
            <div className="min-w-0 flex-1 space-y-1">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                    {WEBHOOK_EVENT_LABELS[delivery.event]}
                    <Badge variant="secondary" className={STATUS_CLASSES[delivery.status]}>
                        {DELIVERY_STATUS_LABELS[delivery.status]}
                    </Badge>
                </p>
                <p className="text-xs text-muted-foreground">
                    {formatRelative(delivery.created_at)} · {delivery.attempts} {delivery.attempts === 1 ? "try" : "tries"}
                    {delivery.response_status !== null && ` · answered ${delivery.response_status}`}
                    {delivery.next_attempt_at && ` · next try ${formatUpcoming(delivery.next_attempt_at)}`}
                </p>
                {delivery.error && delivery.status !== DELIVERY_STATUS.DELIVERED && (
                    <p className="break-words text-xs text-destructive">{delivery.error}</p>
                )}
            </div>
            {delivery.status === DELIVERY_STATUS.FAILED && (
                <Button variant="outline" size="xs" disabled={isRetrying} onClick={() => retryDelivery(delivery)}>
                    <RotateCcw />
                    Send again
                </Button>
            )}
        </li>
    );

    if (isPending) return <Loading />;
    if (rows.length === 0) return <EmptyState icon={Inbox} title="No deliveries" description={DELIVERIES_EMPTY} />;

    return (
        <div className="space-y-3">
            <ul className="divide-y rounded-md border">{rows.map(renderDelivery)}</ul>
            <Pagination page={page} pageSize={DELIVERIES_PAGE_SIZE} total={total} onPageChange={setPage} />
        </div>
    );
};

const DeliveriesDialog = ({ webhookId, onClose }: TDeliveriesDialogProps) => {
    const onOpenChange = (next: boolean) => {
        if (!next) onClose();
    };

    return (
        <Dialog open={webhookId !== null} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-xl">
                <DialogHeader>
                    <DialogTitle>{DELIVERIES_TITLE}</DialogTitle>
                    <DialogDescription>Calls are kept for 30 days. A failed call is tried again up to 5 times.</DialogDescription>
                </DialogHeader>
                {webhookId !== null && <DeliveriesList webhookId={webhookId} />}
            </DialogContent>
        </Dialog>
    );
};

export default DeliveriesDialog;
