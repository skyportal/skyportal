import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_LOCALIZATION_PROPERTIES = "skyportal/FETCH_LOCALIZATION_PROPERTIES";
const FETCH_LOCALIZATION_PROPERTIES_OK =
  "skyportal/FETCH_LOCALIZATION_PROPERTIES_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchLocalizationProperties = (filterParams = {}) =>
  API.GET(
    "/api/localization/properties",
    FETCH_LOCALIZATION_PROPERTIES,
    filterParams,
  );

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_LOCALIZATION_PROPERTIES) {
    dispatch(fetchLocalizationProperties());
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_LOCALIZATION_PROPERTIES_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("localizationProperties", reducer);
