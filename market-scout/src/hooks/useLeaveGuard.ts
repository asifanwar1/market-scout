import { useCallback, useEffect, useRef } from "react";
import { useBlocker } from "react-router-dom";

/**
 * Stops the user leaving a page with unsaved changes: in-app navigation is held until they
 * confirm (render a modal from `blocker`), and closing or reloading the tab gets the browser's
 * own warning. After a successful save, call `allowNextNavigation()` before navigating away.
 */
export const useLeaveGuard = (isDirty: boolean) => {
    const isDirtyRef = useRef(isDirty);
    const allowRef = useRef(false);

    useEffect(() => {
        isDirtyRef.current = isDirty;
    }, [isDirty]);

    const blocker = useBlocker(
        ({ currentLocation, nextLocation }) =>
            !allowRef.current &&
            isDirtyRef.current &&
            currentLocation.pathname !== nextLocation.pathname,
    );

    useEffect(() => {
        if (!isDirty) return;
        const warn = (event: BeforeUnloadEvent) => event.preventDefault();
        window.addEventListener("beforeunload", warn);
        return () => window.removeEventListener("beforeunload", warn);
    }, [isDirty]);

    const allowNextNavigation = useCallback(() => {
        allowRef.current = true;
    }, []);

    return { blocker, allowNextNavigation };
};
