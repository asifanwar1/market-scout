import { AlertTriangle, FileSpreadsheet, Loader2, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { formatCount, pluralize } from "@/utils/format.utils";
import type { TNewImport } from "./NewImport.Container";

type TFileStepProps = {
    page: TNewImport;
};

const FileStep = ({ page }: TFileStepProps) => {
    const { file, preview, fileError, isReading, chooseFile, resetFile } = page;
    const inputRef = useRef<HTMLInputElement>(null);
    const [isDragging, setIsDragging] = useState(false);

    const pick = (files: FileList | null) => {
        const chosen = files?.[0];
        if (chosen) void chooseFile(chosen);
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>1 · The file</CardTitle>
                <CardDescription>A CSV or Excel (.xlsx) file with one business per row and a header row on top.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
                <input
                    ref={inputRef}
                    id="import-file"
                    type="file"
                    accept=".csv,.xlsx,.xlsm,.txt"
                    className="sr-only"
                    onChange={(event) => {
                        pick(event.target.files);
                        event.target.value = ""; // choosing the same file again should still react
                    }}
                />

                {!file && (
                    <button
                        type="button"
                        onClick={() => inputRef.current?.click()}
                        onDragOver={(event) => {
                            event.preventDefault();
                            setIsDragging(true);
                        }}
                        onDragLeave={() => setIsDragging(false)}
                        onDrop={(event) => {
                            event.preventDefault();
                            setIsDragging(false);
                            pick(event.dataTransfer.files);
                        }}
                        className={cn(
                            "flex w-full flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors hover:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
                            isDragging && "border-primary bg-primary/5",
                        )}
                    >
                        <Upload className="size-6 text-muted-foreground" />
                        <span className="font-medium">Choose a file, or drop it here</span>
                        <span className="text-sm text-muted-foreground">.csv or .xlsx, up to 10 MB</span>
                    </button>
                )}

                {file && (
                    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3">
                        <div className="flex min-w-0 items-center gap-3">
                            {isReading ? (
                                <Loader2 className="size-5 shrink-0 animate-spin text-muted-foreground" />
                            ) : (
                                <FileSpreadsheet className="size-5 shrink-0 text-primary" />
                            )}
                            <div className="min-w-0">
                                <p className="truncate font-medium">{file.name}</p>
                                <p className="text-sm text-muted-foreground">
                                    {isReading
                                        ? "Reading the file…"
                                        : preview
                                          ? `${pluralize(preview.row_count, "row", "rows")}, ${formatCount(preview.columns.length)} columns`
                                          : ""}
                                </p>
                            </div>
                        </div>
                        <Button variant="outline" size="sm" onClick={resetFile} disabled={isReading}>
                            Choose a different file
                        </Button>
                    </div>
                )}

                {fileError && (
                    <div role="alert" className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm">
                        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
                        <p>{fileError}</p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

export default FileStep;
