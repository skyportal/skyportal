import * as API from "../../API";

const FETCH_PUBLIC_SOURCE_PAGE = "skyportal/FETCH_PUBLIC_SOURCE_PAGE";
const GENERATE_PUBLIC_SOURCE_PAGE = "skyportal/GENERATE_PUBLIC_SOURCE_PAGE";
const DELETE_PUBLIC_SOURCE_PAGE = "skyportal/DELETE_PUBLIC_SOURCE_PAGE";

export const generatePublicSourcePage = (sourceId, payload) =>
  API.POST(
    `/api/public_pages/source/${sourceId}`,
    GENERATE_PUBLIC_SOURCE_PAGE,
    payload,
  );

export const fetchPublicSourcePage = (sourceId) =>
  API.GET(`/api/public_pages/source/${sourceId}`, FETCH_PUBLIC_SOURCE_PAGE);

export const deletePublicSourcePage = (pageId) =>
  API.DELETE(`/api/public_pages/source/${pageId}`, DELETE_PUBLIC_SOURCE_PAGE);
