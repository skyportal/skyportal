import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_ENUM_TYPES = "skyportal/FETCH_ENUM_TYPES";
const FETCH_ENUM_TYPES_OK = "skyportal/FETCH_ENUM_TYPES_OK";

// eslint-disable-next-line import/prefer-default-export
export function fetchEnumTypes() {
  return API.GET(`/api/enum_types`, FETCH_ENUM_TYPES);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_ENUM_TYPES) {
    dispatch(fetchEnumTypes());
  }
});

const reducer = (state = { enum_types: [] }, action) => {
  switch (action.type) {
    case FETCH_ENUM_TYPES_OK: {
      const enum_types = action.data;
      return {
        ...state,
        enum_types,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("enum_types", reducer);
