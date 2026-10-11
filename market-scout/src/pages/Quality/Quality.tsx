import PageHeader from "@/components/custom/PageHeader";
import DuplicatesCard from "./Components/DuplicatesCard";
import QualitySettingsCard from "./Components/QualitySettingsCard";
import ScoringCard from "./Components/ScoringCard";
import { QUALITY_PAGE_DESCRIPTION, QUALITY_PAGE_TITLE } from "./Quality.constants";

const Quality = () => {
    return (
        <div className="space-y-6">
            <PageHeader title={QUALITY_PAGE_TITLE} description={QUALITY_PAGE_DESCRIPTION} />
            <DuplicatesCard />
            <ScoringCard />
            <QualitySettingsCard />
        </div>
    );
};

export default Quality;
