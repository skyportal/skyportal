import * as API from "../API";
import store from "../store";

const FETCH_LOGINFO = "skyportal/FETCH_LOGINFO";
const FETCH_LOGINFO_OK = "skyportal/FETCH_LOGINFO_OK";

// eslint-disable-next-line import/prefer-default-export
export function fetchLogInfo() {
  return API.GET("/api/loginfo", FETCH_LOGINFO);
}

function reducer(state = {}, action) {
  switch (action.type) {
    case FETCH_LOGINFO_OK: {
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

store.injectReducer("logInfo", reducer);
