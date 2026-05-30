import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

const FETCH_LOCALIZATION_TAGS = "skyportal/FETCH_LOCALIZATION_TAGS";
const FETCH_LOCALIZATION_TAGS_OK = "skyportal/FETCH_LOCALIZATION_TAGS_OK";

export const fetchLocalizationTags = (filterParams = {}) =>
  API.GET("/api/localization/tags", FETCH_LOCALIZATION_TAGS, filterParams);

// Websocket message handler
messageHandler.add(
  (actionType: string, payload: any, dispatch: AppDispatch) => {
    if (actionType === FETCH_LOCALIZATION_TAGS) {
      dispatch(fetchLocalizationTags());
    }
  },
);

type LocalizationTagsState = any;

interface LocalizationTagsAction {
  type: string;
  data?: any;
}

const reducer = (
  state: LocalizationTagsState = null,
  action: LocalizationTagsAction,
): LocalizationTagsState => {
  switch (action.type) {
    case FETCH_LOCALIZATION_TAGS_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("localizationTags", reducer);
