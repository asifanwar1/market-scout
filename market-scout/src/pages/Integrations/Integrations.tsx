import PageHeader from "@/components/custom/PageHeader";
import ApiHelpCard from "./Components/ApiHelpCard";
import ApiKeysCard from "./Components/ApiKeysCard";
import WebhooksCard from "./Components/WebhooksCard";
import { INTEGRATIONS_PAGE_DESCRIPTION, INTEGRATIONS_PAGE_TITLE } from "./Integrations.constants";

const Integrations = () => {
    return (
        <div className="space-y-6">
            <PageHeader title={INTEGRATIONS_PAGE_TITLE} description={INTEGRATIONS_PAGE_DESCRIPTION} />
            <ApiKeysCard />
            <WebhooksCard />
            <ApiHelpCard />
        </div>
    );
};

export default Integrations;
