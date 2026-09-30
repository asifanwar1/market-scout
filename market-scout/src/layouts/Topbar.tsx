import { useLocation } from "react-router-dom";

import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { getPageTitle } from "@/constants/page-title.constants";

const Topbar = () => {
    const { pathname } = useLocation();

    return (
        <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b bg-background/95 px-4 backdrop-blur">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-5" />
            <span className="text-sm font-medium text-muted-foreground">
                {getPageTitle(pathname)}
            </span>
        </header>
    );
};

export default Topbar;
