import messageHandler from "baselayer/MessageHandler";

import * as API from "../../API";
import store from "../../store";

const FETCH_PUBLIC_RELEASES = "skyportal/FETCH_PUBLIC_RELEASES";
const FETCH_PUBLIC_RELEASES_OK = "skyportal/FETCH_PUBLIC_RELEASES_OK";
const SUBMIT_PUBLIC_RELEASE = "skyportal/SUBMIT_PUBLIC_RELEASE";
const UPDATE_PUBLIC_RELEASE = "skyportal/UPDATE_PUBLIC_RELEASE";
const DELETE_PUBLIC_RELEASE = "skyportal/DELETE_PUBLIC_RELEASE";

const REFRESH_PUBLIC_RELEASES = "skyportal/REFRESH_PUBLIC_RELEASES";

export const fetchPublicReleases = () =>
  API.GET("/api/public_pages/release", FETCH_PUBLIC_RELEASES);

export const submitPublicRelease = (payload) =>
  API.POST("/api/public_pages/release", SUBMIT_PUBLIC_RELEASE, payload);

export const updatePublicRelease = (releaseId, payload) =>
  API.PATCH(
    `/api/public_pages/release/${releaseId}`,
    UPDATE_PUBLIC_RELEASE,
    payload,
  );

export const deletePublicRelease = (releaseId) =>
  API.DELETE(`/api/public_pages/release/${releaseId}`, DELETE_PUBLIC_RELEASE);

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_PUBLIC_RELEASES) {
    dispatch(fetchPublicReleases());
  }
});

const reducer = (state = [], action) => {
  switch (action.type) {
    case FETCH_PUBLIC_RELEASES_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("publicReleases", reducer);
