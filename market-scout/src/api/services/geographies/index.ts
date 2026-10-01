import { ENDPOINTS } from "@/constants/endpoints.constants";
import { request } from "@/api/client/request";
import type { TApiArgs } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import type {
    TCreateGeographyBody,
    TUpdateGeographyBody,
} from "./geographies.request.types";
import type {
    TGeographyNode,
    TGeographyTreeResponse,
} from "./geographies.response.types";
import { GEOGRAPHY_QUERY_KEYS } from "./queryKeys";

export const GetGeographyTree = async () => {
    return request<TGeographyTreeResponse>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.GEOGRAPHIES.TREE,
    });
};

export const CreateGeography = async (body: TCreateGeographyBody) => {
    return request<TGeographyNode, TCreateGeographyBody>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.GEOGRAPHIES.ROOT,
        body,
    });
};

export const UpdateGeography = async ({
    id,
    body,
}: TApiArgs<TUpdateGeographyBody>) => {
    return request<TGeographyNode, TUpdateGeographyBody>({
        method: HTTP_METHODS.PUT,
        url: ENDPOINTS.GEOGRAPHIES.detail(id),
        body,
    });
};

export const DeleteGeography = async ({ id }: TApiArgs) => {
    return request<void>({
        method: HTTP_METHODS.DELETE,
        url: ENDPOINTS.GEOGRAPHIES.detail(id),
    });
};

export { GEOGRAPHY_QUERY_KEYS };
