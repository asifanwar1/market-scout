import { request } from "@/api/client/request";
import type { TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import type { TBusinessFilters, TBusinessSort, TSortDirection } from "@/api/services/businesses/businesses.request.types";

export type TExportLeadsParams = TBusinessFilters & {
    sort?: TBusinessSort;
    direction?: TSortDirection;
};

/** The leads matching these filters, as a CSV file. */
export const ExportLeadsCsv = async (params: TExportLeadsParams) => {
    return request<Blob>({
        method: HTTP_METHODS.GET,
        url: "/exports/leads.csv",
        params: params as TQueryParams,
        responseType: "blob",
        // The failure body arrives as a Blob the default handler can't read; the caller shows it.
        silent: true,
    });
};
