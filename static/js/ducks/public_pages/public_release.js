import * as API from "../../API";

const FETCH_PUBLIC_RELEASES = "skyportal/FETCH_PUBLIC_RELEASES";
const CREATE_PUBLIC_RELEASE = "skyportal/CREATE_PUBLIC_RELEASE";
const DELETE_PUBLIC_RELEASE = "skyportal/DELETE_PUBLIC_RELEASE";

export const fetchPublicReleases = () =>
  API.GET("/api/public_pages/release", FETCH_PUBLIC_RELEASES);

export const createPublicRelease = (payload) =>
  API.POST("/api/public_pages/release", CREATE_PUBLIC_RELEASE, payload);

export const deletePublicRelease = (releaseId) =>
  API.DELETE(`/api/public_pages/release/${releaseId}`, DELETE_PUBLIC_RELEASE);
