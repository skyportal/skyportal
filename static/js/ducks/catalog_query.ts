import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

const REFRESH_CATALOG_QUERIES = "skyportal/REFRESH_CATALOG_QUERIES";

const FETCH_CATALOG_QUERIES = "skyportal/FETCH_CATALOG_QUERIES";
const FETCH_CATALOG_QUERIES_OK = "skyportal/FETCH_CATALOG_QUERIES_OK";

const SUBMIT_CATALOG_QUERY = "skyportal/SUBMIT_CATALOG_QUERY";

export const fetchCatalogQueries = () =>
  API.GET("/api/catalog_queries", FETCH_CATALOG_QUERIES);

export function submitCatalogQuery(data: any) {
  return API.POST(`/api/catalog_queries`, SUBMIT_CATALOG_QUERY, data);
}

// Websocket message handler
messageHandler.add(
  (actionType: string, payload: any, dispatch: AppDispatch) => {
    if (actionType === REFRESH_CATALOG_QUERIES) {
      dispatch(fetchCatalogQueries());
    }
  },
);

type CatalogQueryState = Record<string, any>;

interface CatalogQueryAction {
  type: string;
  data?: any;
}

const reducer = (
  state: CatalogQueryState = { catalogQueries: [] },
  action: CatalogQueryAction,
): CatalogQueryState => {
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
