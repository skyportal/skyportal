import * as API from "../../API";

const FETCH_PUBLIC_SOURCE_PAGES = "skyportal/FETCH_PUBLIC_SOURCE_PAGES";
const GENERATE_PUBLIC_SOURCE_PAGE = "skyportal/GENERATE_PUBLIC_SOURCE_PAGE";
const DELETE_PUBLIC_SOURCE_PAGE = "skyportal/DELETE_PUBLIC_SOURCE_PAGE";

export const generatePublicSourcePage = (sourceId, payload) =>
  API.POST(
    `/api/public_pages/source/${sourceId}`,
    GENERATE_PUBLIC_SOURCE_PAGE,
    payload,
  );

export const fetchPublicSourcePages = (sourceId, nbResults) => {
  const nb_results = nbResults ? `nb_results=${nbResults}` : "";
  return API.GET(
    `/api/public_pages/source/${sourceId}?${nb_results}`,
    FETCH_PUBLIC_SOURCE_PAGES,
  );
};

export const deletePublicSourcePage = (pageId) =>
  API.DELETE(`/api/public_pages/source/${pageId}`, DELETE_PUBLIC_SOURCE_PAGE);
