import { lazy } from "react";
import { Navigate, createBrowserRouter, type RouteObject } from "react-router-dom";

import ErrorBoundary from "@/components/custom/ErrorBoundary";
import { USER_ROLE } from "@/constants/user-role.constants";
import AuthLayout from "@/layouts/AuthLayout";
import MainLayout from "@/layouts/MainLayout";
import { APP_ROUTES } from "./appRoutes";
import RequireRole from "./RequireRole";

const Login = lazy(() => import("@/pages/Authentication/Login"));
const Leads = lazy(() => import("@/pages/Leads"));
const Insights = lazy(() => import("@/pages/Insights"));
const DoNotContact = lazy(() => import("@/pages/DoNotContact"));
const Runs = lazy(() => import("@/pages/Runs"));
const NewRun = lazy(() => import("@/pages/Runs/NewRun"));
const RunDetails = lazy(() => import("@/pages/Runs/RunDetails"));
const Imports = lazy(() => import("@/pages/Imports"));
const NewImport = lazy(() => import("@/pages/Imports/NewImport"));
const ImportDetails = lazy(() => import("@/pages/Imports/ImportDetails"));
const Profiles = lazy(() => import("@/pages/Profiles"));
const ProfileEditor = lazy(() => import("@/pages/Profiles/ProfileEditor"));
const Locations = lazy(() => import("@/pages/Locations"));
const Sources = lazy(() => import("@/pages/Sources"));
const Sheets = lazy(() => import("@/pages/Sheets"));
const Users = lazy(() => import("@/pages/Users"));
const NotFound = lazy(() => import("@/pages/NotFound"));

export const routes: RouteObject[] = [
    {
        element: <AuthLayout />,
        errorElement: <ErrorBoundary />,
        children: [{ path: APP_ROUTES.LOGIN, element: <Login /> }],
    },
    {
        element: <MainLayout />,
        errorElement: <ErrorBoundary />,
        children: [
            {
                index: true,
                element: <Navigate to={APP_ROUTES.LEADS} replace />,
            },
            { path: APP_ROUTES.LEADS, element: <Leads /> },
            { path: APP_ROUTES.INSIGHTS, element: <Insights /> },
            { path: APP_ROUTES.DO_NOT_CONTACT, element: <DoNotContact /> },
            {
                element: <RequireRole roles={[USER_ROLE.ADMIN]} />,
                children: [
                    { path: APP_ROUTES.RUNS, element: <Runs /> },
                    { path: APP_ROUTES.RUNS_NEW, element: <NewRun /> },
                    { path: APP_ROUTES.RUNS_DETAILS, element: <RunDetails /> },
                    { path: APP_ROUTES.IMPORTS, element: <Imports /> },
                    { path: APP_ROUTES.IMPORTS_NEW, element: <NewImport /> },
                    { path: APP_ROUTES.IMPORTS_DETAILS, element: <ImportDetails /> },
                    { path: APP_ROUTES.PROFILES, element: <Profiles /> },
                    { path: APP_ROUTES.PROFILES_NEW, element: <ProfileEditor /> },
                    { path: APP_ROUTES.PROFILES_DETAILS, element: <ProfileEditor /> },
                    { path: APP_ROUTES.LOCATIONS, element: <Locations /> },
                    { path: APP_ROUTES.SOURCES, element: <Sources /> },
                    { path: APP_ROUTES.SHEETS, element: <Sheets /> },
                    { path: APP_ROUTES.USERS, element: <Users /> },
                ],
            },
            { path: "*", element: <NotFound /> },
        ],
    },
];

export const router = createBrowserRouter(routes);
