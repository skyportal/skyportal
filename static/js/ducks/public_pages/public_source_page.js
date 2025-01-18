import messageHandler from "baselayer/MessageHandler";

import * as API from "../../API";
import store from "../../store";

const FETCH_PUBLIC_SOURCE_PAGES = "skyportal/FETCH_PUBLIC_SOURCE_PAGES";
const FETCH_PUBLIC_SOURCE_PAGES_OK = "skyportal/FETCH_PUBLIC_SOURCE_PAGES_OK";
const GENERATE_PUBLIC_SOURCE_PAGE = "skyportal/GENERATE_PUBLIC_SOURCE_PAGE";
const DELETE_PUBLIC_SOURCE_PAGE = "skyportal/DELETE_PUBLIC_SOURCE_PAGE";

const REFRESH_PUBLIC_SOURCE_PAGES = "skyportal/REFRESH_PUBLIC_SOURCE_PAGES";

export const generatePublicSourcePage = (sourceId, payload) =>
  API.POST(
    `/api/public_pages/source/${sourceId}`,
    GENERATE_PUBLIC_SOURCE_PAGE,
    payload,
  );

export const fetchPublicSourcePages = (sourceId) => {
  return API.GET(
    `/api/public_pages/source/${sourceId}`,
    FETCH_PUBLIC_SOURCE_PAGES,
  );
};

export const deletePublicSourcePage = (pageId) =>
  API.DELETE(`/api/public_pages/source/${pageId}`, DELETE_PUBLIC_SOURCE_PAGE);

messageHandler.add((actionType, payload, dispatch, getState) => {
  if (actionType === REFRESH_PUBLIC_SOURCE_PAGES) {
    const { source_id } = payload;
    if (getState().source?.id === source_id) {
      dispatch(fetchPublicSourcePages(source_id));
    }
  }
});

const reducer = (state = [], action) => {
  switch (action.type) {
    case FETCH_PUBLIC_SOURCE_PAGES_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("publicSourceVersions", reducer);
