import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import CredentialsCard from "./Components/CredentialsCard";
import SetupGuide from "./Components/SetupGuide";
import SpreadsheetCard from "./Components/SpreadsheetCard";
import SyncStatusCard from "./Components/SyncStatusCard";
import { SHEETS_PAGE_DESCRIPTION, SHEETS_PAGE_TITLE } from "./Sheets.constants";
import { useSheetsPage } from "./Sheets.Container";

const Sheets = () => {
    const { settings, isReady, isSyncing, isSetupOpenByDefault, syncNow } = useSheetsPage();

    return (
        <div className="max-w-4xl space-y-6">
            <PageHeader title={SHEETS_PAGE_TITLE} description={SHEETS_PAGE_DESCRIPTION} />

            {isReady && settings ? (
                <>
                    <SyncStatusCard settings={settings} isSyncing={isSyncing} onSync={syncNow} />
                    <SetupGuide defaultOpen={isSetupOpenByDefault} />
                    <CredentialsCard settings={settings} />
                    <SpreadsheetCard settings={settings} />
                </>
            ) : (
                <Loading />
            )}
        </div>
    );
};

export default Sheets;
