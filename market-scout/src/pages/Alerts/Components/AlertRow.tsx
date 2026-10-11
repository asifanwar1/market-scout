import { Bell, ExternalLink, Sprout, TrendingUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

import type { TAlert } from "@/api/services/alerts/alerts.response.types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ALERT_KIND, getAlertKindLabel } from "@/constants/alert.constants";
import { cn } from "@/lib/utils";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatRelative } from "@/utils/format.utils";
import { OPEN_LEAD_LABEL } from "../Alerts.constants";

const LEAD_ID_PARAM = "lead";

const KIND_ICONS: Record<string, LucideIcon> = {
    [ALERT_KIND.NEW_LEAD]: Sprout,
    [ALERT_KIND.GROWING]: TrendingUp,
    [ALERT_KIND.REACHABLE]: Bell,
};

type TAlertRowProps = {
    alert: TAlert;
    onOpen: (alert: TAlert) => void;
};

const AlertRow = ({ alert, onOpen }: TAlertRowProps) => {
    const Icon = KIND_ICONS[alert.kind] ?? Bell;
    const leadLink = `${APP_ROUTES.LEADS}?${LEAD_ID_PARAM}=${alert.business_id}`;

    return (
        <li className="flex items-start gap-3 px-4 py-3">
            <span
                className={cn("mt-1.5 size-2 shrink-0 rounded-full", alert.is_read ? "bg-transparent" : "bg-primary")}
                aria-label={alert.is_read ? "Read" : "Unread"}
            />
            <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <div className="min-w-0 flex-1 space-y-1">
                <p className={cn("break-words text-sm", !alert.is_read && "font-medium")}>{alert.message}</p>
                <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="secondary">{getAlertKindLabel(alert.kind)}</Badge>
                    <span>{formatRelative(alert.created_at)}</span>
                </p>
            </div>
            <Button asChild variant="ghost" size="icon-xs" aria-label={`${OPEN_LEAD_LABEL}: ${alert.business_name}`}>
                <Link to={leadLink} onClick={() => onOpen(alert)}>
                    <ExternalLink />
                </Link>
            </Button>
        </li>
    );
};

export default AlertRow;
