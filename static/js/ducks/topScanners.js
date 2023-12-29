import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_TOP_SCANNERS = "skyportal/FETCH_TOP_SCANNERS";
const FETCH_TOP_SCANNERS_OK = "skyportal/FETCH_TOP_SCANNERS_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchTopScanners = () =>
  API.GET("/api/internal/source_savers", FETCH_TOP_SCANNERS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_TOP_SCANNERS) {
    dispatch(fetchTopScanners());
  }
});

const reducer = (state = { sourceViews: [] }, action) => {
  switch (action.type) {
    case FETCH_TOP_SCANNERS_OK: {
      const scanners = action.data;
      return {
        scanners,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("topScanners", reducer);
