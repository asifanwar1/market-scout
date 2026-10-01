import type { TSource } from "@/api/services/sources/sources.response.types";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import SourceCard from "./Components/SourceCard";
import { SOURCES_PAGE_DESCRIPTION, SOURCES_PAGE_TITLE } from "./Sources.constants";
import { useSourcesPage } from "./Sources.Container";

const Sources = () => {
    const { isPending, sources } = useSourcesPage();

    const renderSource = (source: TSource) => <SourceCard key={source.key} source={source} />;

    return (
        <div className="max-w-4xl space-y-6">
            <PageHeader title={SOURCES_PAGE_TITLE} description={SOURCES_PAGE_DESCRIPTION} />

            {isPending ? <Loading /> : <div className="space-y-4">{sources.map(renderSource)}</div>}
        </div>
    );
};

export default Sources;
