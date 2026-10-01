export type THttpMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

export type TQueryParams = {
    [key: string]: string | number | boolean | null | undefined;
};

export type TRequestHeaders = {
    [key: string]: string;
};

export type TApiArgs<TBody = undefined, TParams = undefined> = {
    id?: number;
    key?: string;
    body?: TBody;
    params?: TParams;
};

export type WithSignal<T> = T & { signal?: AbortSignal };

export type TListResponse<T> = {
    data: T[];
    count: number;
};

export type TQueryKeyPart = string | number | boolean | null | undefined;

export type TQueryKey = ReadonlyArray<TQueryKeyPart>;
