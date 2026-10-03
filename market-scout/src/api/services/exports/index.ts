import { ENDPOINTS } from "@/constants/endpoints.constants";
import { request } from "@/api/client/request";
import type { TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import type { TBusinessFilters, TBusinessSort, TSortDirection } from "@/api/services/businesses/businesses.request.types";

export type TExportLeadsParams = TBusinessFilters & {
    sort?: TBusinessSort;
    direction?: TSortDirection;
};

const exportLeads = async (url: string, params: TExportLeadsParams) => {
    return request<Blob>({
        method: HTTP_METHODS.GET,
        url,
        params: params as TQueryParams,
        responseType: "blob",
        silent: true,
    });
};

export const ExportLeadsCsv = (params: TExportLeadsParams) => exportLeads(ENDPOINTS.EXPORTS.LEADS_CSV, params);

export const ExportLeadsXlsx = (params: TExportLeadsParams) => exportLeads(ENDPOINTS.EXPORTS.LEADS_XLSX, params);
