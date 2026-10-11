import { Ban } from "lucide-react";

import type { TApiKey } from "@/api/services/apiKeys/apiKeys.response.types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate, formatRelative } from "@/utils/format.utils";

const PREFIX_ELLIPSIS = "…";

type TApiKeyRowProps = {
    apiKey: TApiKey;
    onRevoke: (key: TApiKey) => void;
};

const ApiKeyRow = ({ apiKey, onRevoke }: TApiKeyRowProps) => {
    const isRevoked = apiKey.revoked_at !== null;

    return (
        <li className="flex items-start gap-3 px-4 py-3">
            <div className="min-w-0 flex-1 space-y-1">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                    {apiKey.name}
                    <Badge variant="secondary">{apiKey.can_write ? "Can change leads" : "Read only"}</Badge>
                    {isRevoked && (
                        <Badge variant="secondary" className="bg-destructive/10 text-destructive">
                            Revoked
                        </Badge>
                    )}
                </p>
                <p className="text-xs text-muted-foreground">
                    <span className="font-mono">
                        {apiKey.prefix}
                        {PREFIX_ELLIPSIS}
                    </span>
                    {" · "}created {formatDate(apiKey.created_at)}
                    {" · "}
                    {apiKey.last_used_at ? `last used ${formatRelative(apiKey.last_used_at)}` : "never used"}
                </p>
            </div>
            {!isRevoked && (
                <Button variant="ghost" size="icon-xs" aria-label={`Revoke ${apiKey.name}`} onClick={() => onRevoke(apiKey)}>
                    <Ban />
                </Button>
            )}
        </li>
    );
};

export default ApiKeyRow;
