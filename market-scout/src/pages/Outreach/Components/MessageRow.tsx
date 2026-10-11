import { ExternalLink, Mail, MessageCircle } from "lucide-react";
import { Link } from "react-router-dom";

import type { TOutreachMessage } from "@/api/services/outreach/outreach.response.types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MESSAGE_STATUS, OUTREACH_CHANNEL } from "@/constants/outreach.constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatPhone, formatRelative } from "@/utils/format.utils";
import { describeMessage, previewText, statusLabel } from "@/utils/outreach.utils";

const LEAD_ID_PARAM = "lead";
const OPEN_LEAD_LABEL = "Open lead";
const UNKNOWN_SENDER = "Someone";

const STATUS_CLASSES: Record<string, string> = {
    [MESSAGE_STATUS.SENT]: "bg-success text-success-foreground",
    [MESSAGE_STATUS.NOT_SENT]: "bg-muted text-muted-foreground",
    [MESSAGE_STATUS.OPENED]: "bg-warning text-warning-foreground",
};

type TMessageRowProps = {
    message: TOutreachMessage;
};

const MessageRow = ({ message }: TMessageRowProps) => {
    const isEmail = message.channel === OUTREACH_CHANNEL.EMAIL;
    const Icon = isEmail ? Mail : MessageCircle;
    const leadLink = `${APP_ROUTES.LEADS}?${LEAD_ID_PARAM}=${message.business_id}`;
    const target = isEmail ? message.to_value : formatPhone(message.to_value);
    const detail = describeMessage(message, target);

    return (
        <li className="flex items-start gap-3 px-4 py-3">
            <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <div className="min-w-0 flex-1 space-y-1">
                <p className="truncate text-sm font-medium">{message.business_name}</p>
                <p className="break-words text-sm text-muted-foreground">{previewText(message.body)}</p>
                <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                    <Badge variant="secondary" className={STATUS_CLASSES[message.status]}>
                        {statusLabel(message.status)}
                    </Badge>
                    <span>{detail}</span>
                    <span>
                        {message.created_by?.full_name ?? UNKNOWN_SENDER} · {formatRelative(message.created_at)}
                    </span>
                </p>
            </div>
            <Button asChild variant="ghost" size="icon-xs" aria-label={`${OPEN_LEAD_LABEL}: ${message.business_name}`}>
                <Link to={leadLink}>
                    <ExternalLink />
                </Link>
            </Button>
        </li>
    );
};

export default MessageRow;
