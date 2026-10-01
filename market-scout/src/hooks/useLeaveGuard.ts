import { useEffect, useRef } from "react";
import { useBlocker } from "react-router-dom";

export const useLeaveGuard = (isDirty: boolean) => {
    const allowRef = useRef(false);

    const blocker = useBlocker(
        ({ currentLocation, nextLocation }) =>
            !allowRef.current && isDirty && currentLocation.pathname !== nextLocation.pathname,
    );

    useEffect(() => {
        if (!isDirty) return;
        const warn = (event: BeforeUnloadEvent) => event.preventDefault();
        window.addEventListener("beforeunload", warn);
        return () => window.removeEventListener("beforeunload", warn);
    }, [isDirty]);

    const allowNextNavigation = () => {
        allowRef.current = true;
    };

    return { blocker, allowNextNavigation };
};
