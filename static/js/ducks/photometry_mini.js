import * as API from "../API";
import store from "../store";

const FETCH_SOURCE_PHOTOMETRY_MINI = "skyportal/FETCH_SOURCE_PHOTOMETRY_MINI";
const FETCH_SOURCE_PHOTOMETRY_MINI_OK =
  "skyportal/FETCH_SOURCE_PHOTOMETRY_MINI_OK";
const CLEAR_PHOTOMETRY_MINI = "skyportal/CLEAR_PHOTOMETRY_MINI";

export function fetchSourcePhotometryMini(id) {
  return API.GET(
    `/api/sources/${id}/photometry`,
    FETCH_SOURCE_PHOTOMETRY_MINI,
    {
      format: "mag",
      magsys: "ab",
      individualOrSeries: "both",
      includeOwnerInfo: false,
      includeStreamInfo: false,
      includeValidationInfo: false,
      includeAnnotationInfo: false,
      includeExtinctionInfo: false,
      deduplicatePhotometry: false,
      phaseFoldData: false,
    },
  );
}

export function clearPhotometryMini(sourceIds = null) {
  return {
    type: CLEAR_PHOTOMETRY_MINI,
    sourceIds,
  };
}

const reducer = (state = {}, action) => {
  switch (action.type) {
    case FETCH_SOURCE_PHOTOMETRY_MINI_OK: {
      // only keep the following fields: id, obj_id, filter, limiting_mag, mag, magerr, mjd, origin
      const photometry = (action?.data || []).map((datum) => ({
        id: datum.id,
        obj_id: datum.obj_id,
        filter: datum.filter,
        limiting_mag: datum.limiting_mag,
        mag: datum.mag,
        magerr: datum.magerr,
        mjd: datum.mjd,
        origin: ["None", ""].includes(datum.origin) ? null : datum.origin,
      }));
      // get the sourceID from the parameters of the action
      const sourceID = action?.parameters?.endpoint?.split("/")[3];
      if (sourceID) {
        return {
          ...state,
          [sourceID]: photometry,
        };
      }
      return state;
    }
    case CLEAR_PHOTOMETRY_MINI: {
      const { sourceIds } = action;
      // If no sourceIds provided, clear everything
      if (!sourceIds) {
        return {};
      }
      // Otherwise clear specific IDs
      const newState = { ...state };
      if (Array.isArray(sourceIds)) {
        sourceIds.forEach((id) => {
          delete newState[id];
        });
      }
      return newState;
    }
    default:
      return state;
  }
};

store.injectReducer("photometry_mini", reducer);
