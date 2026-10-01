import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type TStatusBadgeProps = {
    label: string;
    className?: string;
};

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
