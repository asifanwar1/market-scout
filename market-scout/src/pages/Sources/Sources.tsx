import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import { useGetSources } from "@/hooks/api/catalog.queries";
import SourceCard from "./SourceCard";

const Sources = () => {
    const { data, isPending } = useGetSources();
    const sources = data?.data ?? [];

    return (
        <div className="max-w-4xl space-y-6">
            <PageHeader
                title="Sources"
                description="Where Market Scout looks for businesses. Free sources work out of the box; add an API key to use a paid one, and switch back to free ones any time."
            />

            {isPending ? (
                <Loading />
            ) : (
                <div className="space-y-4">
                    {sources.map((source) => (
                        <SourceCard key={source.key} source={source} />
                    ))}
                </div>
            )}
        </div>
    );
};

export default Sources;
