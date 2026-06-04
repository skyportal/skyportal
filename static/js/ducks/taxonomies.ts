import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_TAXONOMIES = "skyportal/REFRESH_TAXONOMIES";

const FETCH_TAXONOMIES = "skyportal/FETCH_TAXONOMIES";
const FETCH_TAXONOMIES_OK = "skyportal/FETCH_TAXONOMIES_OK";

const SUBMIT_TAXONOMY = "skyportal/SUBMIT_TAXONOMY";

const MODIFY_TAXONOMY = "skyportal/MODIFY_TAXONOMY";

const DELETE_TAXONOMY = "skyportal/DELETE_TAXONOMY";

export const modifyTaxonomy = (id: number | string, params: any) =>
  API.PUT(`/api/taxonomy/${id}`, MODIFY_TAXONOMY, params);

export function deleteTaxonomy(id: number | string) {
  return API.DELETE(`/api/taxonomy/${id}`, DELETE_TAXONOMY);
}

export const fetchTaxonomies = () => API.GET("/api/taxonomy", FETCH_TAXONOMIES);

export const submitTaxonomy = (params: Record<string, any> = {}) =>
  API.POST(`/api/taxonomy`, SUBMIT_TAXONOMY, params);

// Websocket message handler
messageHandler.add((actionType: string, _payload: any, dispatch: any) => {
  if (actionType === REFRESH_TAXONOMIES) {
    dispatch(fetchTaxonomies());
  }
});

interface TaxonomiesAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (
  state: Record<string, any> = { taxonomyList: [] },
  action: TaxonomiesAction,
) => {
  switch (action.type) {
    case FETCH_TAXONOMIES_OK: {
      const taxonomyList = action.data;
      return {
        ...state,
        taxonomyList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("taxonomies", reducer);
