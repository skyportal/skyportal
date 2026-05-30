import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_ENUM_TYPES = "skyportal/FETCH_ENUM_TYPES";
const FETCH_ENUM_TYPES_OK = "skyportal/FETCH_ENUM_TYPES_OK";

export function fetchEnumTypes() {
  return API.GET(`/api/enum_types`, FETCH_ENUM_TYPES);
}

// Websocket message handler
messageHandler.add((actionType: any, payload: any, dispatch: any) => {
  if (actionType === FETCH_ENUM_TYPES) {
    dispatch(fetchEnumTypes());
  }
});

interface EnumTypesState {
  enum_types: any;
}

interface EnumTypesAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (
  state: EnumTypesState = { enum_types: [] },
  action: EnumTypesAction,
): EnumTypesState => {
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
