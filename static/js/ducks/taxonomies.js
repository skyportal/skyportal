import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_TAXONOMIES = "skyportal/REFRESH_TAXONOMIES";

const FETCH_TAXONOMIES = "skyportal/FETCH_TAXONOMIES";
const FETCH_TAXONOMIES_OK = "skyportal/FETCH_TAXONOMIES_OK";

const SUBMIT_TAXONOMY = "skyportal/SUBMIT_TAXONOMY";

const MODIFY_TAXONOMY = "skyportal/MODIFY_TAXONOMY";

const DELETE_TAXONOMY = "skyportal/DELETE_TAXONOMY";

export const modifyTaxonomy = (id, params) =>
  API.PUT(`/api/taxonomy/${id}`, MODIFY_TAXONOMY, params);

export function deleteTaxonomy(id) {
  return API.DELETE(`/api/taxonomy/${id}`, DELETE_TAXONOMY);
}

// eslint-disable-next-line import/prefer-default-export
export const fetchTaxonomies = () => API.GET("/api/taxonomy", FETCH_TAXONOMIES);

export const submitTaxonomy = (params = {}) =>
  API.POST(`/api/taxonomy`, SUBMIT_TAXONOMY, params);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_TAXONOMIES) {
    dispatch(fetchTaxonomies());
  }
});

const reducer = (state = { taxonomyList: [] }, action) => {
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
