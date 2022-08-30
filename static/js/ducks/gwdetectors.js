import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_GWDETECTORS = "skyportal/REFRESH_GWDETECTORS";

const FETCH_GWDETECTORS = "skyportal/FETCH_GWDETECTORS";
const FETCH_GWDETECTORS_OK = "skyportal/FETCH_GWDETECTORS_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchGWDetectors = () =>
  API.GET("/api/gwdetector", FETCH_GWDETECTORS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_GWDETECTORS) {
    dispatch(fetchGWDetectors());
  }
});

const reducer = (state = { gwdetectorList: [] }, action) => {
  switch (action.type) {
    case FETCH_GWDETECTORS_OK: {
      const gwdetectorList = action.data;
      return {
        ...state,
        gwdetectorList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("gwdetectors", reducer);
