import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import authSlice, { type AuthSliceType } from "./auth.slice";
import Config from "../Config";

export const sliceResetFns = new Set<() => void>([]);

export const resetAllSlices = () => {
    sliceResetFns.forEach((resetFn) => {
        resetFn();
    });
};

export const useStore = create<AuthSliceType>()(
    persist(
        (...args) => ({
            ...authSlice(...args),
        }),
        {
            name: Config.PERSIST_KEY,
            storage: createJSONStorage(() => localStorage),
        },
    ),
);

export default useStore;
