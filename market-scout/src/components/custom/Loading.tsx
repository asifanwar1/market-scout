import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

type TLoadingProps = {
    className?: string;
    label?: string;
};

const Loading = ({ className, label = "Loading" }: TLoadingProps) => {
    return (
        <div
            role="status"
            aria-live="polite"
            className={cn(
                "flex min-h-40 w-full items-center justify-center gap-2 text-muted-foreground",
                className,
            )}
        >
            <Loader2 className="size-5 animate-spin" />
            <span className="text-sm">{label}…</span>
        </div>
    );
};

export default Loading;
