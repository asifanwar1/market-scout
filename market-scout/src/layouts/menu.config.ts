import {
    BarChart3,
    FileSpreadsheet,
    Layers,
    MapPin,
    Plug,
    Radar,
    ShieldOff,
    UserCog,
    Users,
    type LucideIcon,
} from "lucide-react";

import { USER_ROLE, type UserRole } from "@/constants/user-role.constants";
import { APP_ROUTES } from "@/routes/appRoutes";

export type TMenuItem = {
    label: string;
    icon: LucideIcon;
    path: APP_ROUTES;
};

export type TMenuGroup = {
    label: string;
    // Roles that see the group; omitted means everyone.
    roles?: UserRole[];
    items: TMenuItem[];
};

export const menuGroups: TMenuGroup[] = [
    {
        label: "Work",
        items: [
            { label: "Leads", icon: Users, path: APP_ROUTES.LEADS },
            { label: "Insights", icon: BarChart3, path: APP_ROUTES.INSIGHTS },
            { label: "Do not contact", icon: ShieldOff, path: APP_ROUTES.DO_NOT_CONTACT },
        ],
    },
    {
        label: "Administration",
        roles: [USER_ROLE.ADMIN],
        items: [
            { label: "Runs", icon: Radar, path: APP_ROUTES.RUNS },
            { label: "Profiles", icon: Layers, path: APP_ROUTES.PROFILES },
            { label: "Locations", icon: MapPin, path: APP_ROUTES.LOCATIONS },
            { label: "Sources", icon: Plug, path: APP_ROUTES.SOURCES },
            { label: "Google Sheet", icon: FileSpreadsheet, path: APP_ROUTES.SHEETS },
            { label: "Users", icon: UserCog, path: APP_ROUTES.USERS },
        ],
    },
];
