import { request } from "@/api/client/request";
import type { TApiArgs, TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import { IMPORT_QUERY_KEYS } from "./queryKeys";
import type { TGetImportsParams, TImportOptions } from "./imports.request.types";
import type { TGetImportsResponse, TImport, TImportPreview } from "./imports.response.types";

const fileForm = (file: File, options?: TImportOptions) => {
    const form = new FormData();
    form.append("file", file);
    if (options) form.append("options", JSON.stringify(options));
    return form;
};

/** Read the file and get a first guess at which column is which. Nothing is stored. */
export const PreviewImport = async ({ file }: { file: File }) => {
    return request<TImportPreview, FormData>({
        method: HTTP_METHODS.POST,
        url: "/imports/preview",
        body: fileForm(file),
        // A file the server cannot read is explained on the screen, not in a toast.
        silent: true,
    });
};

export const CreateImport = async ({ file, options }: { file: File; options: TImportOptions }) => {
    return request<TImport, FormData>({
        method: HTTP_METHODS.POST,
        url: "/imports/",
        body: fileForm(file, options),
    });
};

export const GetImports = async (params?: TGetImportsParams) => {
    return request<TGetImportsResponse>({
        method: HTTP_METHODS.GET,
        url: "/imports/",
        params: params as TQueryParams,
    });
};

export const GetImport = async ({ id }: TApiArgs) => {
    return request<TImport>({
        method: HTTP_METHODS.GET,
        url: `/imports/${id}`,
    });
};

export const CancelImport = async ({ id }: TApiArgs) => {
    return request<TImport>({
        method: HTTP_METHODS.POST,
        url: `/imports/${id}/cancel`,
    });
};

export { IMPORT_QUERY_KEYS };
