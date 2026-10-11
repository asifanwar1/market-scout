import { KeyRound, Loader2, Plus } from "lucide-react";
import { useState } from "react";

import type { TApiKey } from "@/api/services/apiKeys/apiKeys.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { API_KEY_NAME_MAX_LENGTH } from "@/constants/integration.constants";
import { useCreateApiKey, useGetApiKeys, useRevokeApiKey } from "@/hooks/api/integrations.queries";
import { showToast } from "@/lib/toast";
import {
    KEY_CREATED_DESCRIPTION,
    KEY_CREATED_TITLE,
    KEY_REVOKE_DESCRIPTION,
    KEY_REVOKE_TITLE,
    KEY_WRITE_HELP,
    KEY_WRITE_LABEL,
    KEYS_DESCRIPTION,
    KEYS_EMPTY,
    KEYS_TITLE,
} from "../Integrations.constants";
import ApiKeyRow from "./ApiKeyRow";
import ShownOnceDialog from "./ShownOnceDialog";

const NAME_PLACEHOLDER = "e.g. Billing app";

type TCreateKeyDialogProps = {
    open: boolean;
    onClose: () => void;
    onCreated: (token: string) => void;
};

const CreateKeyForm = ({ onClose, onCreated }: Omit<TCreateKeyDialogProps, "open">) => {
    const { mutateAsync: create, isPending } = useCreateApiKey();
    const [name, setName] = useState("");
    const [canWrite, setCanWrite] = useState(false);
    const canSave = name.trim().length > 0 && !isPending;

    const save = async () => {
        const created = await create({ name: name.trim(), can_write: canWrite });
        onCreated(created.token);
    };

    return (
        <DialogContent>
            <DialogHeader>
                <DialogTitle>New API key</DialogTitle>
                <DialogDescription>Name it after what will use it, so you know which one to revoke later.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
                <div className="space-y-1.5">
                    <Label htmlFor="key-name">Name</Label>
                    <Input
                        id="key-name"
                        maxLength={API_KEY_NAME_MAX_LENGTH}
                        value={name}
                        placeholder={NAME_PLACEHOLDER}
                        onChange={(event) => setName(event.target.value)}
                    />
                </div>
                <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                        <Label htmlFor="key-write">{KEY_WRITE_LABEL}</Label>
                        <p className="text-xs text-muted-foreground">{KEY_WRITE_HELP}</p>
                    </div>
                    <Switch id="key-write" checked={canWrite} onCheckedChange={setCanWrite} />
                </div>
            </div>
            <DialogFooter>
                <Button variant="ghost" onClick={onClose}>
                    Cancel
                </Button>
                <Button disabled={!canSave} onClick={save}>
                    {isPending && <Loader2 className="animate-spin" />}
                    Create key
                </Button>
            </DialogFooter>
        </DialogContent>
    );
};

const CreateKeyDialog = ({ open, onClose, onCreated }: TCreateKeyDialogProps) => {
    const onOpenChange = (next: boolean) => {
        if (!next) onClose();
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            {open && <CreateKeyForm onClose={onClose} onCreated={onCreated} />}
        </Dialog>
    );
};

const ApiKeysCard = () => {
    const { data, isPending } = useGetApiKeys();
    const { mutateAsync: revoke, isPending: isRevoking } = useRevokeApiKey();
    const [isCreating, setIsCreating] = useState(false);
    const [token, setToken] = useState<string | null>(null);
    const [revoking, setRevoking] = useState<TApiKey | null>(null);

    const keys = data?.data ?? [];

    const onCreated = (value: string) => {
        setIsCreating(false);
        setToken(value);
    };

    const confirmRevoke = async () => {
        if (revoking === null) return;
        await revoke(revoking.id);
        setRevoking(null);
        showToast.success("Key revoked");
    };

    const renderKey = (key: TApiKey) => <ApiKeyRow key={key.id} apiKey={key} onRevoke={setRevoking} />;

    return (
        <Card>
            <CardHeader>
                <CardTitle>{KEYS_TITLE}</CardTitle>
                <CardDescription>{KEYS_DESCRIPTION}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <Button onClick={() => setIsCreating(true)}>
                    <Plus />
                    New API key
                </Button>
                {isPending ? (
                    <Loading />
                ) : keys.length > 0 ? (
                    <ul className="divide-y rounded-md border">{keys.map(renderKey)}</ul>
                ) : (
                    <EmptyState icon={KeyRound} title={KEYS_EMPTY} />
                )}
            </CardContent>

            <CreateKeyDialog open={isCreating} onClose={() => setIsCreating(false)} onCreated={onCreated} />
            <ShownOnceDialog
                value={token}
                title={KEY_CREATED_TITLE}
                description={KEY_CREATED_DESCRIPTION}
                label="API key"
                onClose={() => setToken(null)}
            />
            <ConfirmationModal
                open={revoking !== null}
                destructive
                title={KEY_REVOKE_TITLE}
                description={KEY_REVOKE_DESCRIPTION}
                confirmText="Revoke"
                isLoading={isRevoking}
                onConfirm={confirmRevoke}
                onClose={() => setRevoking(null)}
            />
        </Card>
    );
};

export default ApiKeysCard;
