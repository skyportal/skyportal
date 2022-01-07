import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_GALAXIES = "skyportal/FETCH_GALAXIES";
const FETCH_GALAXIES_OK = "skyportal/FETCH_GALAXIES_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchGalaxies = () => API.GET("/api/galaxy_catalog", FETCH_GALAXIES);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_GALAXIES) {
    dispatch(fetchGalaxies());
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_GALAXIES_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("galaxies", reducer);
