import * as API from "../API";
import store from "../store";

const FETCH_TNS_INFO = "skyportal/FETCH_TNS_INFO";
const FETCH_TNS_INFO_OK = "skyportal/FETCH_TNS_INFO_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchTNSInfo = (objID) =>
  API.GET(`/api/tns_info/${objID}`, FETCH_TNS_INFO);

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_TNS_INFO_OK: {
      if (state === null) {
        return action.data;
      }
      return {
        ...state,
        ...action.data,
      };
    }
    default: {
      return state;
    }
  }
};

store.injectReducer("tnsInfo", reducer);
