import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_MOVING_OBJECTS = "skyportal/REFRESH_MOVING_OBJECTS";

const FETCH_MOVING_OBJECTS = "skyportal/FETCH_MOVING_OBJECTS";
const FETCH_MOVING_OBJECTS_OK = "skyportal/FETCH_MOVING_OBJECTS_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchMovingObjects = (filterParams = {}) =>
  API.GET("/api/moving_object", FETCH_MOVING_OBJECTS, filterParams);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_MOVING_OBJECTS) {
    dispatch(fetchMovingObjects());
  }
});

const reducer = (
  state = {
    movingObjects: {},
  },
  action,
) => {
  switch (action.type) {
    case FETCH_MOVING_OBJECTS_OK: {
      const moving_objects = action.data;
      return {
        ...state,
        movingObjects: moving_objects,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("moving_objects", reducer);
