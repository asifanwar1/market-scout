import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type TStatusBadgeProps = {
    label: string;
    className?: string;
};

/** A pill coloured by its own classes (see the *.constants files for the palettes). */
const StatusBadge = ({ label, className }: TStatusBadgeProps) => {
    return (
        <Badge
            variant="secondary"
            className={cn("border-transparent font-medium", className)}
        >
            {label}
        </Badge>
    );
};

export default StatusBadge;
