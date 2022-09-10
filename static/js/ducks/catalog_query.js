import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_CATALOG_QUERIES = "skyportal/REFRESH_CATALOG_QUERIES";

const FETCH_CATALOG_QUERIES = "skyportal/FETCH_CATALOG_QUERIES";
const FETCH_CATALOG_QUERIES_OK = "skyportal/FETCH_CATALOG_QUERIES_OK";

const SUBMIT_CATALOG_QUERY = "skyportal/SUBMIT_CATALOG_QUERY";

// eslint-disable-next-line import/prefer-default-export
export const fetchCatalogQueries = () =>
  API.GET("/api/catalog_queries", FETCH_CATALOG_QUERIES);

export function submitCatalogQuery(data) {
  return API.POST(`/api/catalog_queries`, SUBMIT_CATALOG_QUERY, data);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_CATALOG_QUERIES) {
    dispatch(fetchCatalogQueries());
  }
});

const reducer = (state = { catalogQueries: [] }, action) => {
  switch (action.type) {
    case FETCH_CATALOG_QUERIES_OK: {
      const catalogQueries = action.data;
      return {
        ...state,
        catalogQueries,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("catalogQueries", reducer);
