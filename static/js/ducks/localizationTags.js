import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_LOCALIZATION_TAGS = "skyportal/FETCH_LOCALIZATION_TAGS";
const FETCH_LOCALIZATION_TAGS_OK = "skyportal/FETCH_LOCALIZATION_TAGS_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchLocalizationTags = (filterParams = {}) =>
  API.GET("/api/localization/tags", FETCH_LOCALIZATION_TAGS, filterParams);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_LOCALIZATION_TAGS) {
    dispatch(fetchLocalizationTags());
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_LOCALIZATION_TAGS_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("localizationTags", reducer);
