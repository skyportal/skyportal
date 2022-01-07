import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_GALAXIES = "skyportal/FETCH_GALAXIES";
const FETCH_GALAXIES_OK = "skyportal/FETCH_GALAXIES_OK";

// eslint-disable-next-line import/prefer-default-export
export function fetchGalaxies(
  dateobs = null,
  catalog_name = "CLU_mini",
  filterParams = {}
) {
  filterParams.localizationDateobs = dateobs;
  filterParams.localizationCumprob = 0.95;
  filterParams.catalog_name = catalog_name;

  filterParams.includeGeojson = true;
  return API.GET("/api/galaxy_catalog", FETCH_GALAXIES, filterParams);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { gcnEvent } = getState();

  if (actionType === FETCH_GALAXIES) {
    if (gcnEvent && gcnEvent.id === payload.gcnEvent.id) {
      dispatch(fetchGalaxies(gcnEvent.dateobs));
    }
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
