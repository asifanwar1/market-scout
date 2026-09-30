import { request } from "@/api/client/request";
import type { TApiArgs, TQueryParams, WithSignal } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import type {
    TBulkUpdateBody,
    TDoNotContactBody,
    TGetBusinessesParams,
    TUpdateBusinessBody,
} from "./businesses.request.types";
import type {
    TAssignedUser,
    TBulkUpdateResponse,
    TBusinessDetail,
    TDoNotContactResponse,
    TGetBusinessesResponse,
} from "./businesses.response.types";
import { BUSINESS_QUERY_KEYS } from "./queryKeys";

export const GetBusinesses = async (
    params?: WithSignal<TGetBusinessesParams>,
) => {
    const { signal, ...urlParams } = params || {};

    return request<TGetBusinessesResponse>({
        method: HTTP_METHODS.GET,
        url: "/businesses/",
        params: urlParams as TQueryParams,
        signal,
    });
};

export const GetBusiness = async ({ id }: TApiArgs) => {
    return request<TBusinessDetail>({
        method: HTTP_METHODS.GET,
        url: `/businesses/${id}`,
        // A lead can legitimately vanish while its panel is open (someone marked it do not
        // contact); the panel explains that inline, so no error toast on top.
        silent: true,
    });
};

export const UpdateBusiness = async ({
    id,
    body,
}: TApiArgs<TUpdateBusinessBody>) => {
    return request<TBusinessDetail, TUpdateBusinessBody>({
        method: HTTP_METHODS.PATCH,
        url: `/businesses/${id}`,
        body,
    });
};

export const BulkUpdateBusinesses = async (body: TBulkUpdateBody) => {
    return request<TBulkUpdateResponse, TBulkUpdateBody>({
        method: HTTP_METHODS.POST,
        url: "/businesses/bulk-update",
        body,
    });
};

export const GetAssignees = async () => {
    return request<TAssignedUser[]>({
        method: HTTP_METHODS.GET,
        url: "/businesses/assignees",
    });
};

export const MarkDoNotContact = async ({
    id,
    body,
}: TApiArgs<TDoNotContactBody>) => {
    return request<TDoNotContactResponse, TDoNotContactBody>({
        method: HTTP_METHODS.POST,
        url: `/businesses/${id}/do-not-contact`,
        body: body ?? {},
    });
};

export { BUSINESS_QUERY_KEYS };
