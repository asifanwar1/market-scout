import { ChevronDown, Download, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EXPORT_BUTTON_LABEL, EXPORT_OPTIONS } from "../Leads.constants";
import type { TLeadsPage } from "../Leads.Container";

type TExportMenuProps = {
    page: TLeadsPage;
};

const ExportMenu = ({ page }: TExportMenuProps) => {
    const { exportLeads, isExporting, isExportDisabled } = page;

    const renderOption = (option: (typeof EXPORT_OPTIONS)[number]) => (
        <DropdownMenuItem key={option.format} onSelect={() => void exportLeads(option.format)}>
            {option.label}
        </DropdownMenuItem>
    );

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="outline" disabled={isExportDisabled}>
                    {isExporting ? <Loader2 className="animate-spin" /> : <Download />}
                    {EXPORT_BUTTON_LABEL}
                    <ChevronDown />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-40">
                {EXPORT_OPTIONS.map(renderOption)}
            </DropdownMenuContent>
        </DropdownMenu>
    );
};

export default ExportMenu;
