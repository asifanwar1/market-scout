import { Navigate, Outlet } from "react-router-dom";

import type { UserRole } from "@/constants/user-role.constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { useStore } from "@/store";

type TRequireRoleProps = {
    roles: UserRole[];
};

// A guard for what the sidebar already hides: typing the URL by hand mustn't get around it.
// (The server enforces the same rule; this just spares the user a wall of 403 toasts.)
const RequireRole = ({ roles }: TRequireRoleProps) => {
    const role = useStore((state) => state.user?.role);

    if (!role || !roles.includes(role)) {
        return <Navigate to={APP_ROUTES.LEADS} replace />;
    }
    return <Outlet />;
};

export default RequireRole;
