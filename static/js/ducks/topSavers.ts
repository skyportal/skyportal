import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

const FETCH_TOP_SAVERS = "skyportal/FETCH_TOP_SAVERS";
const FETCH_TOP_SAVERS_OK = "skyportal/FETCH_TOP_SAVERS_OK";

export const fetchTopSavers = () =>
  API.GET("/api/internal/source_savers", FETCH_TOP_SAVERS);

// Websocket message handler
messageHandler.add(
  (actionType: string, payload: any, dispatch: AppDispatch) => {
    if (actionType === FETCH_TOP_SAVERS) {
      dispatch(fetchTopSavers());
    }
  },
);

type TopSaversState = Record<string, any>;

interface TopSaversAction {
  type: string;
  data?: any;
}

const reducer = (
  state: TopSaversState = { savers: [] },
  action: TopSaversAction,
): TopSaversState => {
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
