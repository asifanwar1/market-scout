import { Suspense, useState } from "react";
import { Navigate, Outlet, useNavigate } from "react-router-dom";

import ConfirmationModal from "@/components/custom/ConfirmationModal";
import Loading from "@/components/custom/Loading";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { useGetMe, useLogout } from "@/hooks/api/auth.queries";
import { APP_ROUTES } from "@/routes/appRoutes";
import { useStore } from "@/store";
import AppSidebar from "./AppSidebar";
import Topbar from "./Topbar";

const MainLayout = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);
    const navigate = useNavigate();
    const logout = useLogout();
    const [showLogout, setShowLogout] = useState(false);
    useGetMe();

    if (!isAuthenticated) {
        return <Navigate to={APP_ROUTES.LOGIN} replace />;
    }

    const handleLogout = () => {
        logout();
        setShowLogout(false);
        navigate(APP_ROUTES.LOGIN, { replace: true });
    };

    return (
        <SidebarProvider>
            <AppSidebar onLogoutClick={() => setShowLogout(true)} />
            <SidebarInset>
                <Topbar />
                <main className="flex-1 p-4 md:p-6">
                    <Suspense fallback={<Loading />}>
                        <Outlet />
                    </Suspense>
                </main>
            </SidebarInset>

            <ConfirmationModal
                open={showLogout}
                title="Sign out?"
                description="You'll need to sign in again to keep working."
                confirmText="Sign out"
                onConfirm={handleLogout}
                onClose={() => setShowLogout(false)}
            />
        </SidebarProvider>
    );
};

export default MainLayout;
