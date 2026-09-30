import type { ReactNode } from "react";

type TPageHeaderProps = {
    title: string;
    description?: string;
    actions?: ReactNode;
};

const PageHeader = ({ title, description, actions }: TPageHeaderProps) => {
    return (
        <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
                <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
                {description && (
                    <p className="mt-1 text-sm text-muted-foreground">
                        {description}
                    </p>
                )}
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
    );
};

export default PageHeader;
