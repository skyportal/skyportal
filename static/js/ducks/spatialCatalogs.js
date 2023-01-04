import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const REFRESH_SPATIAL_CATALOG = "skyportal/REFRESH_SPATIAL_CATALOG";

export const DELETE_SPATIAL_CATALOG = "skyportal/DELETE_SPATIAL_CATALOG";

export const FETCH_SPATIAL_CATALOG = "skyportal/FETCH_SPATIAL_CATALOG";
export const FETCH_SPATIAL_CATALOG_OK = "skyportal/FETCH_SPATIAL_CATALOG_OK";

const REFRESH_SPATIAL_CATALOGS = "skyportal/REFRESH_SPATIAL_CATALOGS";

const FETCH_SPATIAL_CATALOGS = "skyportal/FETCH_SPATIAL_CATALOGS";
const FETCH_SPATIAL_CATALOGS_OK = "skyportal/FETCH_SPATIAL_CATALOGS_OK";

const UPLOAD_SPATIAL_CATALOGS = "skyportal/UPLOAD_SPATIAL_CATALOGS";

export const fetchSpatialCatalog = (id) =>
  API.GET(`/api/spatial_catalog/${id}`, FETCH_SPATIAL_CATALOG);

// eslint-disable-next-line import/prefer-default-export
export const fetchSpatialCatalogs = (filterParams = {}) =>
  API.GET("/api/spatial_catalog", FETCH_SPATIAL_CATALOGS, filterParams);

export function uploadSpatialCatalogs(data) {
  return API.POST(`/api/spatial_catalog/ascii`, UPLOAD_SPATIAL_CATALOGS, data);
}

export function deleteSpatialCatalog(id) {
  return API.DELETE(`/api/spatial_catalog/${id}`, DELETE_SPATIAL_CATALOG);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  if (actionType === REFRESH_SPATIAL_CATALOGS) {
    dispatch(fetchSpatialCatalogs());
  }
  const { spatialCatalog } = getState();
  if (actionType === FETCH_SPATIAL_CATALOG) {
    dispatch(fetchSpatialCatalog(spatialCatalog.id));
  }
  if (actionType === REFRESH_SPATIAL_CATALOG) {
    const loaded_spatial_catalog = spatialCatalog?.id;

    if (loaded_spatial_catalog === payload.spatialCatalog_id) {
      dispatch(fetchSpatialCatalog(spatialCatalog.id));
    }
  }
});

const reducer_spatialCatalogs = (state = null, action) => {
  switch (action.type) {
    case FETCH_SPATIAL_CATALOGS_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("spatialCatalogs", reducer_spatialCatalogs);

const reducer_spatialCatalog = (state = null, action) => {
  switch (action.type) {
    case FETCH_SPATIAL_CATALOG_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("spatialCatalog", reducer_spatialCatalog);
