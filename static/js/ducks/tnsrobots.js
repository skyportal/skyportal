import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_TNSROBOTS = "skyportal/FETCH_TNSROBOTS";
const FETCH_TNSROBOTS_OK = "skyportal/FETCH_TNSROBOTS_OK";

const REFRESH_TNSROBOTS = "skyportal/REFRESH_TNSROBOTS";

// eslint-disable-next-line import/prefer-default-export
export const fetchTNSRobots = (params = {}) =>
  API.GET("/api/tns_robot", FETCH_TNSROBOTS, params);

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_TNSROBOTS) {
    dispatch(fetchTNSRobots());
  }
});

const reducer = (state = { tnsrobotList: [] }, action) => {
  switch (action.type) {
    case FETCH_TNSROBOTS_OK: {
      const tnsrobotList = action.data;
      return {
        ...state,
        tnsrobotList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("tnsrobots", reducer);
