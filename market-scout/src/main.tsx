import "@fontsource-variable/inter";
import { isAxiosError } from "axios";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { NuqsAdapter } from "nuqs/adapters/react";

import "./theme.css";

import App from "./App.tsx";
import { ApiClientProvider, ToastProvider } from "./providers";

// Every failed API call is already reported by the axios interceptor (a toast), but callers that
// `await` a mutation still see the rejection. Mark those as handled so the console stays for
// genuine bugs.
window.addEventListener("unhandledrejection", (event) => {
    if (isAxiosError(event.reason)) event.preventDefault();
});

createRoot(document.getElementById("root")!).render(
    <StrictMode>
        <ApiClientProvider>
            <NuqsAdapter>
                <ToastProvider>
                    <App />
                </ToastProvider>
            </NuqsAdapter>
        </ApiClientProvider>
    </StrictMode>,
);
