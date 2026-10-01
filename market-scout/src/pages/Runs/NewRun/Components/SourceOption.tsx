import type { TSource } from "@/api/services/sources/sources.response.types";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { getUnavailableReason } from "@/utils/sources.utils";

type TSourceOptionProps = {
    source: TSource;
    isChecked: boolean;
    onToggle: (key: string) => void;
};

const SourceOption = ({ source, isChecked, onToggle }: TSourceOptionProps) => {
    const inputId = `source-${source.key}`;

    return (
        <div className="flex items-start gap-2">
            <Checkbox
                id={inputId}
                className="mt-0.5"
                disabled={!source.is_available}
                checked={isChecked}
                onCheckedChange={() => onToggle(source.key)}
            />
            <Label htmlFor={inputId} className="block font-normal">
                <span className="font-medium">
                    {source.name}
                    {source.is_paid && (
                        <span className="ml-2 rounded bg-warning px-1.5 py-0.5 text-xs font-normal text-warning-foreground">Paid</span>
                    )}
                </span>
                <span className="block text-xs text-muted-foreground">{source.is_available ? source.description : getUnavailableReason(source)}</span>
            </Label>
        </div>
    );
};

export default SourceOption;
