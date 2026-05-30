import * as API from "../API";
import store from "../store";

const FETCH_SOURCE_PHOTOMETRY_MINIMAL =
  "skyportal/FETCH_SOURCE_PHOTOMETRY_MINIMAL";
const FETCH_SOURCE_PHOTOMETRY_MINIMAL_OK =
  "skyportal/FETCH_SOURCE_PHOTOMETRY_MINIMAL_OK";
const CLEAR_PHOTOMETRY_MINIMAL = "skyportal/CLEAR_PHOTOMETRY_MINIMAL";

export function fetchSourcePhotometryMinimal(id: number | string) {
  return API.GET(
    `/api/sources/${id}/photometry`,
    FETCH_SOURCE_PHOTOMETRY_MINIMAL,
    {
      format: "plot",
      magsys: "ab",
      individualOrSeries: "both",
      includeSuperObjsPhotometry: true,
    },
  );
}

export function clearPhotometryMinimal(sourceIds: any = null) {
  return {
    type: CLEAR_PHOTOMETRY_MINIMAL,
    sourceIds,
  };
}

interface PhotometryMinimalAction {
  type: string;
  data?: any;
  sourceIds?: any;
  parameters?: any;
  [key: string]: any;
}

const reducer = (
  state: Record<string, any> = {},
  action: PhotometryMinimalAction,
) => {
  switch (action.type) {
    case FETCH_SOURCE_PHOTOMETRY_MINIMAL_OK: {
      // only keep the following fields: id, obj_id, filter, limiting_mag, mag, magerr, mjd, origin
      const photometry = (action?.data || []).map((datum: any) => ({
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
    case CLEAR_PHOTOMETRY_MINIMAL: {
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

store.injectReducer("photometry_minimal", reducer);
