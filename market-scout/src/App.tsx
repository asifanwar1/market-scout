import { Suspense } from "react";
import { RouterProvider } from "react-router-dom";

import Loading from "@/components/custom/Loading";
import { TooltipProvider } from "@/components/ui/tooltip";
import { router } from "@/routes/routes";

const App = () => {
    return (
        <TooltipProvider>
            <Suspense fallback={<Loading className="min-h-screen" />}>
                <RouterProvider router={router} />
            </Suspense>
        </TooltipProvider>
    );
};

export default App;
