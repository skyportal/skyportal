/**
 * Redux store types.
 *
 * `RootState` types only the slices that are STILL plain Redux. Every migrated
 * duck now lives in the RTK Query cache (`skyportalApi`) and must be read via
 * its generated hook/selector, NOT via `state.<slice>`. There is intentionally
 * no index-signature fallback: a read of a migrated slice must be a type error.
 */
import type { ThunkAction, ThunkDispatch } from "redux-thunk";
import type { Store, UnknownAction } from "redux";

import type { skyportalApi } from "../api/skyportalApi";

export interface RootState {
  // RTK Query cache slice. All endpoints injected by migrated ducks live here.
  skyportalApi: ReturnType<typeof skyportalApi.reducer>;

  // --- Slices that are still plain Redux (typed from their reducer state) ---
  sidebar: { open: boolean };
  logo: { rotateLogo: boolean };
  classifications: {
    taxonomy?: any;
    scaleProbabilities?: any;
    [key: string]: any;
  };
  hydration: { hydratedList: any[]; hydrated: boolean };
  notifications: {
    notes: {
      id: number;
      note: string;
      type: string;
      tag: string;
    }[];
  };
  // Retained client-UI portion of the candidates duck.
  candidates: {
    selectedAnnotationSortOptions: any;
    filterFormData: any;
  };
}

/**
 * The runtime store is the redux Store enhanced with a dynamic `injectReducer`
 * (each duck registers its own slice reducer at import time). Ducks cast the
 * default `store` import to this until store.js itself is converted to TS:
 *   (store as unknown as AppStore).injectReducer("slice", reducer);
 */
export interface AppStore extends Store<RootState, UnknownAction> {
  // Reducers registered dynamically by each duck at import time.
  reducers: { [key: string]: (state: any, action: any) => any };
  // Each duck types its own slice/action; accept any reducer shape here.
  injectReducer: (
    key: string,
    reducer: (state: any, action: any) => any,
  ) => void;
}

/** Thunk-aware dispatch (the app uses redux-thunk). */
export type AppDispatch = ThunkDispatch<RootState, unknown, UnknownAction>;

/** Return type for thunk action creators: `(): AppThunk<Promise<Result>>`. */
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  UnknownAction
>;
