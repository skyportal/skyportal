import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_TOP_SAVERS = "skyportal/FETCH_TOP_SAVERS";
const FETCH_TOP_SAVERS_OK = "skyportal/FETCH_TOP_SAVERS_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchTopSavers = () =>
  API.GET("/api/internal/source_savers", FETCH_TOP_SAVERS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_TOP_SAVERS) {
    dispatch(fetchTopSavers());
  }
});

const reducer = (state = { savers: [] }, action) => {
  switch (action.type) {
    case FETCH_TOP_SAVERS_OK: {
      const savers = action.data;
      return {
        savers,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("topSavers", reducer);
