import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import CredentialsCard from "./CredentialsCard";
import SetupGuide from "./SetupGuide";
import { useSheetsPage } from "./Sheets.Container";
import SpreadsheetCard from "./SpreadsheetCard";
import SyncStatusCard from "./SyncStatusCard";

const Sheets = () => {
    const { settings, isPending, isSyncing, syncNow } = useSheetsPage();

    return (
        <div className="max-w-4xl space-y-6">
            <PageHeader
                title="Google Sheet"
                description="A live copy of your leads in Google Sheets, for anyone who prefers a spreadsheet. Everyone can also download the leads as a CSV file from the Leads page."
            />

            {isPending || !settings ? (
                <Loading />
            ) : (
                <>
                    <SyncStatusCard settings={settings} isSyncing={isSyncing} onSync={syncNow} />
                    <SetupGuide defaultOpen={!settings.is_configured} />
                    <CredentialsCard settings={settings} />
                    <SpreadsheetCard settings={settings} />
                </>
            )}
        </div>
    );
};

export default Sheets;
