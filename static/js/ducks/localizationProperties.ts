import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_LOCALIZATION_PROPERTIES = "skyportal/FETCH_LOCALIZATION_PROPERTIES";
const FETCH_LOCALIZATION_PROPERTIES_OK =
  "skyportal/FETCH_LOCALIZATION_PROPERTIES_OK";

export const fetchLocalizationProperties = (
  filterParams: Record<string, any> = {},
) =>
  API.GET(
    "/api/localization/properties",
    FETCH_LOCALIZATION_PROPERTIES,
    filterParams,
  );

// Websocket message handler
messageHandler.add((actionType: any, _payload: any, dispatch: any) => {
  if (actionType === FETCH_LOCALIZATION_PROPERTIES) {
    dispatch(fetchLocalizationProperties());
  }
});

const reducer = (
  state: any = null,
  action: { type: string; data?: any },
): any => {
  switch (action.type) {
    case FETCH_LOCALIZATION_PROPERTIES_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("localizationProperties", reducer);
