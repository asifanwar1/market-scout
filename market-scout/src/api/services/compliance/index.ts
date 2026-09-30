import { request } from "@/api/client/request";
import type { TApiArgs, TListResponse, TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import type { TDoNotContactResponse } from "../businesses/businesses.response.types";
import { COMPLIANCE_QUERY_KEYS } from "./queryKeys";

export type TGetDoNotContactParams = {
    page?: number;
    limit?: number;
    search?: string;
};

// Exactly one of phone / email.
export type TAddDoNotContactBody = {
    phone?: string;
    email?: string;
    reason?: string | null;
};

export const GetDoNotContact = async (params?: TGetDoNotContactParams) => {
    return request<TListResponse<TDoNotContactResponse>>({
        method: HTTP_METHODS.GET,
        url: "/compliance/do-not-contact",
        params: params as TQueryParams,
    });
};

export const AddDoNotContact = async (body: TAddDoNotContactBody) => {
    return request<TDoNotContactResponse, TAddDoNotContactBody>({
        method: HTTP_METHODS.POST,
        url: "/compliance/do-not-contact",
        body,
    });
};

export const RemoveDoNotContact = async ({ id }: TApiArgs) => {
    return request<void>({
        method: HTTP_METHODS.DELETE,
        url: `/compliance/do-not-contact/${id}`,
    });
};

export { COMPLIANCE_QUERY_KEYS };
