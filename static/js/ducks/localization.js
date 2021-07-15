import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_LOCALIZATION = "skyportal/FETCH_LOCALIZATION";
export const FETCH_LOCALIZATION_OK = "skyportal/FETCH_LOCALIZATION_OK";

export const fetchLocalization = (dateobs, localization_name) =>
  API.GET(
    `/api/localization/${dateobs}/name/${localization_name}`,
    FETCH_LOCALIZATION
  );

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { localization } = getState();

  if (actionType === FETCH_LOCALIZATION) {
    dispatch(
      fetchLocalization(localization.dateobs, localization.localization_name)
    );
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_LOCALIZATION_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("localization", reducer);
