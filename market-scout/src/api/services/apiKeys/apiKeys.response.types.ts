import type { TListResponse } from "@/api/types/common";

export type TApiKey = {
    id: number;
    name: string;
    prefix: string;
    can_write: boolean;
    created_at: string;
    last_used_at: string | null;
    revoked_at: string | null;
};

export type TApiKeyCreated = TApiKey & {
    token: string;
};

export type TGetApiKeysResponse = TListResponse<TApiKey>;
