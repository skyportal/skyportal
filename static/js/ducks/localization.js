import * as API from "../API";
import store from "../store";

const DELETE_LOCALIZATION = "skyportal/DELETE_LOCALIZATION ";

export const FETCH_LOCALIZATION = "skyportal/FETCH_LOCALIZATION";
export const FETCH_LOCALIZATION_OK = "skyportal/FETCH_LOCALIZATION_OK";

export const FETCH_LOCALIZATION_ANALYSIS =
  "skyportal/FETCH_LOCALIZATION_ANALYSIS";
export const FETCH_LOCALIZATION_ANALYSIS_OK =
  "skyportal/FETCH_LOCALIZATION_ANALYSIS_OK";

export const FETCH_LOCALIZATION_OBSPLAN =
  "skyportal/FETCH_LOCALIZATION_OBSPLAN";
export const FETCH_LOCALIZATION_OBSPLAN_OK =
  "skyportal/FETCH_LOCALIZATION_OBSPLAN_OK";

export const POST_LOCALIZATION_FROM_NOTICE =
  "skyportal/POST_LOCALIZATION_FROM_NOTICE";

const typeEnum = {
  analysis: FETCH_LOCALIZATION_ANALYSIS,
  obsplan: FETCH_LOCALIZATION_OBSPLAN,
};

export const fetchLocalization = (
  dateobs,
  localization_name,
  type = "analysis",
) =>
  API.GET(
    `/api/localization/${dateobs}/name/${localization_name}`,
    typeEnum[type],
  );

export function deleteLocalization(dateobs, localization_name) {
  return API.DELETE(
    `/api/localization/${dateobs}/name/${localization_name}`,
    DELETE_LOCALIZATION,
  );
}

export function postLocalizationFromNotice({ dateobs, noticeID }) {
  return API.POST(
    `/api/localization/${dateobs}/notice/${noticeID}`,
    POST_LOCALIZATION_FROM_NOTICE,
  );
}

const reducer = (state = { analysisLoc: null, obsplanLoc: null }, action) => {
  switch (action.type) {
    case FETCH_LOCALIZATION_ANALYSIS_OK: {
      return {
        ...state,
        analysisLoc: action.data,
      };
    }
    case FETCH_LOCALIZATION_OBSPLAN_OK: {
      return {
        ...state,
        obsplanLoc: action.data,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("localization", reducer);
