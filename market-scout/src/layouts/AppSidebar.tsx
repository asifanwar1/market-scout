import { LogOut, Radar } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
} from "@/components/ui/sidebar";
import { APP_ROUTES } from "@/routes/appRoutes";
import { useStore } from "@/store";
import { menuGroups } from "./menu.config";

type TAppSidebarProps = {
    onLogoutClick: () => void;
};

const AppSidebar = ({ onLogoutClick }: TAppSidebarProps) => {
    const { pathname } = useLocation();
    const user = useStore((state) => state.user);

    const visibleGroups = menuGroups.filter(
        (group) => !group.roles || (user && group.roles.includes(user.role)),
    );

    const renderGroup = (group: (typeof visibleGroups)[number]) => {
        const renderItem = (item: (typeof group.items)[number]) => (
            <SidebarMenuItem key={item.path}>
                <SidebarMenuButton
                    asChild
                    tooltip={item.label}
                    isActive={pathname.startsWith(item.path)}
                >
                    <Link to={item.path}>
                        <item.icon />
                        <span>{item.label}</span>
                    </Link>
                </SidebarMenuButton>
            </SidebarMenuItem>
        );
        return (
            <SidebarGroup key={group.label}>
                <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
                <SidebarGroupContent>
                    <SidebarMenu>
                        {group.items.map(renderItem)}
                    </SidebarMenu>
                </SidebarGroupContent>
            </SidebarGroup>
        );
    };
    return (
        <Sidebar collapsible="icon">
            <SidebarHeader>
                <Link
                    to={APP_ROUTES.ROOT}
                    className="flex items-center gap-2 px-2 py-1.5 font-semibold group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
                >
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                        <Radar className="size-4" />
                    </span>
                    <span className="truncate group-data-[collapsible=icon]:hidden">
                        Market Scout
                    </span>
                </Link>
            </SidebarHeader>

            <SidebarContent>
                {visibleGroups.map(renderGroup)}
            </SidebarContent>

            <SidebarFooter>
                <div className="flex items-center gap-2 px-2 py-1.5">
                    <div className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden">
                        <p className="truncate text-sm font-medium">{user?.full_name}</p>
                        <p className="truncate text-xs capitalize text-muted-foreground">
                            {user?.role}
                        </p>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label="Sign out"
                        onClick={onLogoutClick}
                    >
                        <LogOut />
                    </Button>
                </div>
            </SidebarFooter>
        </Sidebar>
    );
};

export default AppSidebar;
