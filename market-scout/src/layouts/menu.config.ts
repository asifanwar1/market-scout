import {
    BadgeCheck,
    BarChart3,
    Bell,
    CalendarCheck,
    CalendarClock,
    FileSpreadsheet,
    FileUp,
    Layers,
    MapPin,
    Plug,
    Send,
    Radar,
    Sparkles,
    ShieldOff,
    UserCog,
    Webhook,
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
    roles?: UserRole[];
    items: TMenuItem[];
};

export const menuGroups: TMenuGroup[] = [
    {
        label: "Work",
        items: [
            { label: "Leads", icon: Users, path: APP_ROUTES.LEADS },
            { label: "Tasks", icon: CalendarCheck, path: APP_ROUTES.TASKS },
            { label: "Alerts", icon: Bell, path: APP_ROUTES.ALERTS },
            { label: "Outreach", icon: Send, path: APP_ROUTES.OUTREACH },
            { label: "Insights", icon: BarChart3, path: APP_ROUTES.INSIGHTS },
            { label: "Do not contact", icon: ShieldOff, path: APP_ROUTES.DO_NOT_CONTACT },
        ],
    },
    {
        label: "Administration",
        roles: [USER_ROLE.ADMIN],
        items: [
            { label: "Runs", icon: Radar, path: APP_ROUTES.RUNS },
            { label: "Repeating searches", icon: CalendarClock, path: APP_ROUTES.SCHEDULES },
            { label: "Imports", icon: FileUp, path: APP_ROUTES.IMPORTS },
            { label: "Profiles", icon: Layers, path: APP_ROUTES.PROFILES },
            { label: "Locations", icon: MapPin, path: APP_ROUTES.LOCATIONS },
            { label: "Sources", icon: Plug, path: APP_ROUTES.SOURCES },
            { label: "Data quality", icon: BadgeCheck, path: APP_ROUTES.QUALITY },
            { label: "Integrations", icon: Webhook, path: APP_ROUTES.INTEGRATIONS },
            { label: "AI assistant", icon: Sparkles, path: APP_ROUTES.AI },
            { label: "Google Sheet", icon: FileSpreadsheet, path: APP_ROUTES.SHEETS },
            { label: "Users", icon: UserCog, path: APP_ROUTES.USERS },
        ],
    },
];
