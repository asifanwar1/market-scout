export type THttpMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

export type TQueryParams = {
    [key: string]: string | number | boolean | null | undefined;
};

export type TRequestHeaders = {
    [key: string]: string;
};

export type TApiArgs<TBody = unknown, TParams = unknown> = {
    id?: number;
    key?: string;
    body?: TBody;
    params?: TParams;
};

export type WithSignal<T> = T & { signal?: AbortSignal };

/** Every list endpoint answers with the page's rows and the total count. */
export type TListResponse<T> = {
    data: T[];
    count: number;
};
