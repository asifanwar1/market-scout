import { useEffect, useState } from "react";
import { DEFAULT_DEBOUNCE_MS } from "@/constants/timing.constants";

export const useDebouncedValue = <T,>(value: T, delayMs = DEFAULT_DEBOUNCE_MS): T => {
    const [debounced, setDebounced] = useState(value);

    useEffect(() => {
        const timer = setTimeout(() => setDebounced(value), delayMs);
        return () => clearTimeout(timer);
    }, [value, delayMs]);

    return debounced;
};
