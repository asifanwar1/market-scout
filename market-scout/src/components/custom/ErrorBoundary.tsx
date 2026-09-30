import { Link, isRouteErrorResponse, useRouteError } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { APP_ROUTES } from "@/routes/appRoutes";

// Rendered by React Router when a page throws while rendering or loading.
const ErrorBoundary = () => {
    const error = useRouteError();
    const message = isRouteErrorResponse(error)
        ? `${error.status} ${error.statusText}`
        : error instanceof Error
          ? error.message
          : "An unexpected error occurred.";

    return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
            <h1 className="text-2xl font-semibold">Something went wrong</h1>
            <p className="max-w-md text-sm text-muted-foreground">{message}</p>
            <Button asChild>
                <Link to={APP_ROUTES.ROOT}>Back to the app</Link>
            </Button>
        </div>
    );
};

export default ErrorBoundary;
