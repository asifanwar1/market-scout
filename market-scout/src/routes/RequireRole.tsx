import { Navigate, Outlet } from "react-router-dom";

import type { UserRole } from "@/constants/user-role.constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { useStore } from "@/store";

type TRequireRoleProps = {
    roles: UserRole[];
};

const RequireRole = ({ roles }: TRequireRoleProps) => {
    const role = useStore((state) => state.user?.role);

    if (!role || !roles.includes(role)) {
        return <Navigate to={APP_ROUTES.LEADS} replace />;
    }
    return <Outlet />;
};

export default RequireRole;
