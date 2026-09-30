import type { PropsWithChildren } from "react";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

const ToastProvider = ({ children }: PropsWithChildren) => {
    return (
        <>
            {children}
            <ToastContainer
                position="top-right"
                autoClose={4000}
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
