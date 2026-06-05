/**
 * Redux store types.
 *
 * `RootState` types the slices that have been migrated/typed so far, and keeps
 * an index-signature fallback so the ~85 ducks that are not yet typed don't
 * break `useAppSelector`. As each duck is converted, add its slice here and
 * (eventually) the fallback can be removed for full coverage.
 */
import type { ThunkAction, ThunkDispatch } from "redux-thunk";
import type { Store, UnknownAction } from "redux";

import type { skyportalApi } from "../api/skyportalApi";
import type { Profile, Group, SourceTag } from "./domain";

export interface ObjectTagsState {
  [index: number]: SourceTag;
}

export interface RootState {
  profile: Profile;
  groups: {
    user: Group[];
    userAccessible: Group[];
    all: Group[];
  };
  objectTags: SourceTag[];
  // RTK Query cache slice. All endpoints injected by migrated ducks live here.
  skyportalApi: ReturnType<typeof skyportalApi.reducer>;
  // Fallback for ducks not yet typed. Replace with concrete slice types as
  // each duck is migrated; delete once every slice is typed.
  [slice: string]: any;
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
