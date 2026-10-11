import { request } from "@/api/client/request";
import type { TApiArgs } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import { ENDPOINTS } from "@/constants/endpoints.constants";
import type { TApiKeyBody } from "./apiKeys.request.types";
import type { TApiKey, TApiKeyCreated, TGetApiKeysResponse } from "./apiKeys.response.types";
import { API_KEY_QUERY_KEYS } from "./queryKeys";

export const GetApiKeys = () => request<TGetApiKeysResponse>({ method: HTTP_METHODS.GET, url: ENDPOINTS.API_KEYS.ROOT });

export const CreateApiKey = (body: TApiKeyBody) =>
    request<TApiKeyCreated, TApiKeyBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.API_KEYS.ROOT, body });

export const RevokeApiKey = ({ id }: TApiArgs) => request<TApiKey>({ method: HTTP_METHODS.DELETE, url: ENDPOINTS.API_KEYS.key(id) });

export { API_KEY_QUERY_KEYS };
