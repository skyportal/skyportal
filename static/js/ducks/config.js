import * as API from "../API";
import store from "../store";

const FETCH_CONFIG = "skyportal/FETCH_CONFIG";
const FETCH_CONFIG_OK = "skyportal/FETCH_CONFIG_OK";

// eslint-disable-next-line import/prefer-default-export
export function fetchConfig() {
  return API.GET("/api/config", FETCH_CONFIG);
}

function reducer(state = {}, action) {
  switch (action.type) {
    case FETCH_CONFIG_OK: {
      const { version, data } = action;
      return {
        ...data,
        version,
      };
    }
    default:
      return state;
  }
}

store.injectReducer("config", reducer);
