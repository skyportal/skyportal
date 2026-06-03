import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

const FETCH_RECURRING_APIS_LIST = "skyportal/FETCH_RECURRING_APIS_LIST";
const FETCH_RECURRING_APIS_LIST_OK = "skyportal/FETCH_RECURRING_APIS_LIST_OK";

const REFRESH_RECURRING_APIS = "skyportal/REFRESH_RECURRING_APIS";

const FETCH_RECURRING_API_OK = "skyportal/FETCH_RECURRING_API_OK";

const SUBMIT_RECURRING_API = "skyportal/SUBMIT_RECURRING_API";

const DELETE_RECURRING_API = "skyportal/DELETE_RECURRING_API";

export const fetchRecurringAPIs = (params = {}) =>
  API.GET("/api/recurring_api", FETCH_RECURRING_APIS_LIST, params);

export const submitRecurringAPI = (run: any) =>
  API.POST(`/api/recurring_api`, SUBMIT_RECURRING_API, run);

export const deleteRecurringAPI = (id: number | string) =>
  API.DELETE(`/api/recurring_api/${id}`, DELETE_RECURRING_API);

messageHandler.add(
  (actionType: string, _payload: any, dispatch: AppDispatch) => {
    if (actionType === REFRESH_RECURRING_APIS) {
      dispatch(fetchRecurringAPIs());
    }
  },
);

interface RecurringApiAction {
  type: string;
  data?: any;
}

const reducer_recurring_api = (
  state: Record<string, any> = {},
  action: RecurringApiAction,
): Record<string, any> => {
  switch (action.type) {
    case FETCH_RECURRING_API_OK: {
      const recurring_api = action.data;
      return {
        ...state,
        ...recurring_api,
      };
    }
    default:
      return state;
  }
};

const reducer_recurring_apis = (
  state: Record<string, any> = { recurringAPIList: [] },
  action: RecurringApiAction,
): Record<string, any> => {
  switch (action.type) {
    case FETCH_RECURRING_APIS_LIST_OK: {
      const recurringAPIList = action.data;
      return {
        ...state,
        recurringAPIList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("recurring_api", reducer_recurring_api);
store.injectReducer("recurring_apis", reducer_recurring_apis);
