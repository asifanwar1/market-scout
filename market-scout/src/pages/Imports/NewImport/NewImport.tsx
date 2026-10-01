import { ArrowLeft, Loader2, Play } from "lucide-react";
import { Link } from "react-router-dom";

import PageHeader from "@/components/custom/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatCount } from "@/utils/format.utils";
import ColumnsStep from "./Components/ColumnsStep";
import FileStep from "./Components/FileStep";
import { useNewImport } from "./NewImport.Container";
import SettingsStep from "./Components/SettingsStep";

const NewImport = () => {
    const page = useNewImport();
    const { preview, hasPreview, mapping, problem, isStarting, isStartDisabled, start } = page;

    return (
        <div className="space-y-6">
            <Button asChild variant="ghost" size="sm" className="-ml-2">
                <Link to={APP_ROUTES.IMPORTS}>
                    <ArrowLeft />
                    All imports
                </Link>
            </Button>

            <PageHeader
                title="New import"
                description="Upload a list of businesses. Nothing is added until you press Start import, and anyone on the do-not-contact list is left out."
            />

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
                <div className="min-w-0 space-y-6">
                    <FileStep page={page} />
                    {hasPreview && preview && (
                        <>
                            <ColumnsStep preview={preview} mapping={mapping} onChange={page.setMapping} />
                            <SettingsStep page={page} />
                        </>
                    )}
                </div>

                <Card className="lg:sticky lg:top-20 lg:self-start">
                    <CardHeader>
                        <CardTitle>Ready to import?</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {!hasPreview || !preview ? (
                            <p className="text-sm text-muted-foreground">Choose a file to begin.</p>
                        ) : (
                            <>
                                <dl className="grid grid-cols-2 gap-3 text-sm">
                                    <div>
                                        <dt className="text-xs text-muted-foreground">Rows in the file</dt>
                                        <dd className="text-2xl font-semibold tabular-nums">{formatCount(preview.row_count)}</dd>
                                    </div>
                                    <div>
                                        <dt className="text-xs text-muted-foreground">Phone columns</dt>
                                        <dd className="text-2xl font-semibold tabular-nums">{mapping.phones.length}</dd>
                                    </div>
                                </dl>
                                {problem ? (
                                    <p role="status" className="rounded-md bg-warning p-2.5 text-sm text-warning-foreground">
                                        {problem}
                                    </p>
                                ) : (
                                    <p className="text-sm text-muted-foreground">
                                        Rows are cleaned and checked first. You will see how many are new, already known or set aside.
                                    </p>
                                )}
                            </>
                        )}
                        <Button className="w-full" size="lg" disabled={isStartDisabled} onClick={start}>
                            {isStarting ? <Loader2 className="animate-spin" /> : <Play />}
                            Start import
                        </Button>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default NewImport;
