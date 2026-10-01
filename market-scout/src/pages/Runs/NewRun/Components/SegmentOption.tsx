import type { TSegment } from "@/api/services/profiles/profiles.response.types";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

type TSegmentOptionProps = {
    segment: TSegment;
    isChecked: boolean;
    onToggle: (slug: string) => void;
};

const SegmentOption = ({ segment, isChecked, onToggle }: TSegmentOptionProps) => {
    const inputId = `segment-${segment.id}`;

    return (
        <div className="flex items-start gap-2">
            <Checkbox id={inputId} className="mt-0.5" checked={isChecked} onCheckedChange={() => onToggle(segment.slug)} />
            <Label htmlFor={inputId} className="block font-normal">
                <span className="font-medium">{segment.name}</span>
                {segment.description && <span className="block text-xs text-muted-foreground">{segment.description}</span>}
            </Label>
        </div>
    );
};

export default SegmentOption;
