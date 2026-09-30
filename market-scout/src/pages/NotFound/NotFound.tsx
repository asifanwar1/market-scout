import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { APP_ROUTES } from "@/routes/appRoutes";

const NotFound = () => {
    return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-6 text-center">
            <p className="text-5xl font-semibold text-muted-foreground">404</p>
            <h1 className="text-xl font-semibold">Page not found</h1>
            <p className="max-w-sm text-sm text-muted-foreground">
                The page you're looking for doesn't exist or has moved.
            </p>
            <Button asChild>
                <Link to={APP_ROUTES.ROOT}>Go to leads</Link>
            </Button>
        </div>
    );
};

export default NotFound;
