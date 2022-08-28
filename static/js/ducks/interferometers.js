import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_INTERFEROMETERS = "skyportal/REFRESH_INTERFEROMETERS";

const FETCH_INTERFEROMETERS = "skyportal/FETCH_INTERFEROMETERS";
const FETCH_INTERFEROMETERS_OK = "skyportal/FETCH_INTERFEROMETERS_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchInterferometers = () =>
  API.GET("/api/interferometer", FETCH_INTERFEROMETERS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_INTERFEROMETERS) {
    dispatch(fetchInterferometers());
  }
});

const reducer = (state = { interferometerList: [] }, action) => {
  switch (action.type) {
    case FETCH_INTERFEROMETERS_OK: {
      const interferometerList = action.data;
      return {
        ...state,
        interferometerList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("interferometers", reducer);
