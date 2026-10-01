import { useGetSources } from "@/hooks/api/catalog.queries";

export const useSourcesPage = () => {
    const { data, isPending } = useGetSources();
    const sources = data?.data ?? [];

    return {
        isPending,
        sources,
    };
};
