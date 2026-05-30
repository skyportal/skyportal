import * as API from "../API";
import store from "../store";

const FETCH_DB_INFO = "skyportal/FETCH_DB_INFO";
const FETCH_DB_INFO_OK = "skyportal/FETCH_DB_INFO_OK";

export function fetchDBInfo() {
  return API.GET("/api/internal/dbinfo", FETCH_DB_INFO);
}

const reducer = (
  state: Record<string, any> = {},
  action: { type: string; data?: any },
): Record<string, any> => {
  switch (action.type) {
    case FETCH_DB_INFO_OK:
      return action.data;
    default:
      return state;
  }
};

store.injectReducer("dbInfo", reducer);
