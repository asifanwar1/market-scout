import type { StateCreator } from "zustand";
import type { UserModel } from "@/api/models/user.model";
import { sliceResetFns } from "./store";

export interface AuthStateType {
    isAuthenticated: boolean;
    token: string | null;
    refreshToken: string | null;
    user: UserModel | null;
}

export interface AuthSliceType extends AuthStateType {
    setAuth: (auth: Partial<AuthStateType>) => void;
    clearAuth: () => void;
}

export const initialAuthState: AuthStateType = {
    isAuthenticated: false,
    token: null,
    refreshToken: null,
    user: null,
};

const authSlice: StateCreator<AuthSliceType, [], [], AuthSliceType> = (
    set,
) => {
    sliceResetFns.add(() => set(initialAuthState));

    return {
        ...initialAuthState,
        setAuth: (auth) => set((state) => ({ ...state, ...auth })),
        clearAuth: () => set(() => ({ ...initialAuthState })),
    };
};

export default authSlice;
