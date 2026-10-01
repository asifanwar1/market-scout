import type { PropsWithChildren } from "react";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import { TOAST_AUTO_CLOSE_MS } from "@/constants/timing.constants";

const ToastProvider = ({ children }: PropsWithChildren) => {
    return (
        <>
            {children}
            <ToastContainer
                position="top-right"
                autoClose={TOAST_AUTO_CLOSE_MS}
                hideProgressBar
                closeOnClick
                pauseOnFocusLoss
                pauseOnHover
                theme="colored"
            />
        </>
    );
};

export default ToastProvider;
