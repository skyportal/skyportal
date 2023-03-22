import * as API from "../API";
import store from "../store";

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
  cached: FETCH_LOCALIZATION,
  analysis: FETCH_LOCALIZATION_ANALYSIS,
  obsplan: FETCH_LOCALIZATION_OBSPLAN,
};

export const fetchLocalization = (
  dateobs,
  localization_name,
  type = "cached"
) =>
  API.GET(
    `/api/localization/${dateobs}/name/${localization_name}`,
    typeEnum[type]
  );

export function postLocalizationFromNotice({ dateobs, noticeID }) {
  return API.POST(
    `/api/localization/${dateobs}/notice/${noticeID}`,
    POST_LOCALIZATION_FROM_NOTICE
  );
}

const reducer = (
  state = { cached: null, analysis: null, obsplan: null },
  action
) => {
  switch (action.type) {
    case FETCH_LOCALIZATION_OK: {
      return {
        ...state,
        cached: action.data,
        analysis:
          state.analysis === null || action.data?.id !== state.analysis?.id
            ? action.data
            : state.analysis,
        obsplan:
          state.obsplan === null || action.data?.id !== state.obsplan?.id
            ? action.data
            : state.obsplan,
      };
    }
    case FETCH_LOCALIZATION_ANALYSIS_OK: {
      return {
        ...state,
        analysis: action.data,
      };
    }
    case FETCH_LOCALIZATION_OBSPLAN_OK: {
      return {
        ...state,
        obsplan: action.data,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("localization", reducer);
