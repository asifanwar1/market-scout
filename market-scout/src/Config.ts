import { DEFAULT_PAGE_LIMIT } from "@/constants/limits.constants";

export type TConfigType = {
    LIMIT: number;
    API_URL: string;
    PERSIST_KEY: string;
};

const Config: TConfigType = {
    PERSIST_KEY: "market-scout-auth",
    LIMIT: Number(import.meta.env.VITE_LIMIT) || DEFAULT_PAGE_LIMIT,
    API_URL: import.meta.env.VITE_API_URL,
};

export default Config;
