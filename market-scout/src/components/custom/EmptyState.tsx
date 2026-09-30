import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type TEmptyStateProps = {
    icon: LucideIcon;
    title: string;
    description?: string;
    action?: ReactNode;
};

const EmptyState = ({ icon: Icon, title, description, action }: TEmptyStateProps) => {
    return (
        <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
            <div className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
                <Icon className="size-6" />
            </div>
            <div>
                <p className="font-medium">{title}</p>
                {description && (
                    <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                        {description}
                    </p>
                )}
            </div>
            {action}
        </div>
    );
};

export default EmptyState;
