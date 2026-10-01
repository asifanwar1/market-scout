import { Suspense } from "react";
import { Navigate, Outlet } from "react-router-dom";

import Loading from "@/components/custom/Loading";
import { APP_ROUTES } from "@/routes/appRoutes";
import { useStore } from "@/store";

const AuthLayout = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    if (isAuthenticated) {
        return <Navigate to={APP_ROUTES.ROOT} replace />;
    }

    return (
        <Suspense fallback={<Loading />}>
            <Outlet />
        </Suspense>
    );
};

export default AuthLayout;
