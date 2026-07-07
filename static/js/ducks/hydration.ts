import store from "../store";

const FINISHED_HYDRATING = "skyportal/FINISHED_HYDRATING";
const VERIFY_HYDRATION = "skyportal/VERIFY_HYDRATION";

// No eager boot prefetch: every page/shell component fetches its own data via
// RTK Query hooks (deduped), so the old hydration burst is unnecessary.
export const DUCKS_TO_HYDRATE = [];

export const NUMBER_OF_DUCKS_TO_HYDRATE = DUCKS_TO_HYDRATE.length;

export function finishedHydrating(ducks: any) {
  return {
    data: ducks,
    type: FINISHED_HYDRATING,
  };
}

export function verifyHydration() {
  return {
    type: VERIFY_HYDRATION,
  };
}

interface HydrationState {
  hydratedList: any[];
  hydrated: boolean;
}

interface HydrationAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (
  state: HydrationState = { hydratedList: [], hydrated: false },
  action: HydrationAction,
): HydrationState => {
  switch (action.type) {
    case FINISHED_HYDRATING: {
      return {
        ...state,
        hydratedList: [...new Set([...state.hydratedList, action.data])],
        hydrated: state.hydratedList.length === NUMBER_OF_DUCKS_TO_HYDRATE,
      };
    }
    case VERIFY_HYDRATION: {
      return {
        ...state,
        hydrated: state?.hydratedList?.length === NUMBER_OF_DUCKS_TO_HYDRATE,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("hydration", reducer);
