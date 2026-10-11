import { Bell, CheckCheck } from "lucide-react";

import type { TAlert } from "@/api/services/alerts/alerts.response.types";
import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { ALL_OPTION_VALUE } from "@/constants";
import AlertRow from "./Components/AlertRow";
import AlertSettingsCard from "./Components/AlertSettingsCard";
import { ALERTS_EMPTY_DESCRIPTION, ALERTS_PAGE_DESCRIPTION, ALERTS_PAGE_TITLE } from "./Alerts.constants";
import { useAlertsPage } from "./Alerts.Container";

const Alerts = () => {
    const {
        alerts,
        total,
        unreadCount,
        hasAlerts,
        unreadOnly,
        kindValue,
        kindOptions,
        page,
        pageSize,
        isPending,
        isAdmin,
        canMarkAll,
        emptyTitle,
        onUnreadChange,
        onKindChange,
        onPageChange,
        onPageSizeChange,
        openAlert,
        markAllRead,
    } = useAlertsPage();

    const renderAlert = (alert: TAlert) => <AlertRow key={alert.id} alert={alert} onOpen={openAlert} />;

    const renderKind = (option: (typeof kindOptions)[number]) => (
        <SelectItem key={option.value} value={option.value}>
            {option.label}
        </SelectItem>
    );

    const markAllAction = (
        <Button variant="outline" disabled={!canMarkAll} onClick={markAllRead}>
            <CheckCheck />
            Mark all read{unreadCount > 0 && ` (${unreadCount})`}
        </Button>
    );

    return (
        <div className="space-y-4">
            <PageHeader title={ALERTS_PAGE_TITLE} description={ALERTS_PAGE_DESCRIPTION} actions={markAllAction} />

            <div className="flex flex-wrap items-center gap-4">
                <Select value={kindValue} onValueChange={onKindChange}>
                    <SelectTrigger className="w-52" aria-label="Filter by kind">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL_OPTION_VALUE}>All kinds</SelectItem>
                        {kindOptions.map(renderKind)}
                    </SelectContent>
                </Select>
                <div className="flex items-center gap-2">
                    <Switch id="alerts-unread" checked={unreadOnly} onCheckedChange={onUnreadChange} />
                    <Label htmlFor="alerts-unread" className="text-sm font-normal">
                        Unread only
                    </Label>
                </div>
            </div>

            <Card className="p-0">
                {isPending ? (
                    <Loading />
                ) : hasAlerts ? (
                    <ul className="divide-y">{alerts.map(renderAlert)}</ul>
                ) : (
                    <EmptyState icon={Bell} title={emptyTitle} description={ALERTS_EMPTY_DESCRIPTION} />
                )}
            </Card>

            {hasAlerts && (
                <Pagination page={page} pageSize={pageSize} total={total} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />
            )}

            {isAdmin && <AlertSettingsCard />}
        </div>
    );
};

export default Alerts;
