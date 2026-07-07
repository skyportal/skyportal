/**
 * Typed Redux hooks. Import these instead of the bare react-redux hooks so
 * that `state` is typed as RootState and dispatch can dispatch thunks.
 *
 *   import { useAppSelector, useAppDispatch } from "../types/hooks";
 *   const profile = useAppSelector((state) => state.profile); // typed Profile
 */
import { useDispatch, useSelector } from "react-redux";
import type { TypedUseSelectorHook } from "react-redux";

import type { RootState, AppDispatch } from "./store";

export const useAppDispatch: () => AppDispatch = useDispatch;
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
