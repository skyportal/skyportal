import * as API from "../API";

const UPDATE_ACCESSIBILITY = "skyportal/UPDATE_ACCESSIBILITY";

const FETCH_ACCESSIBILITY = "skyportal/FETCH_ACCESSIBILITY";

export const updateSourceAccessibility = (sourceId, payload) =>
    API.POST(`/api/sources/${sourceId}/accessibility`, UPDATE_ACCESSIBILITY, payload);

export const fetchSourceAccessibility = (sourceId) =>
    API.GET(`/api/sources/${sourceId}/accessibility`, FETCH_ACCESSIBILITY);
