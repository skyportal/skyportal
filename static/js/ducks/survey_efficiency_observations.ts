import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

const REFRESH_SURVEY_EFFICIENCY_OBSERVATIONS =
  "skyportal/REFRESH_SURVEY_EFFICIENCY_OBSERVATIONS";

const FETCH_SURVEY_EFFICIENCY_OBSERVATIONS =
  "skyportal/FETCH_SURVEY_EFFICIENCY_OBSERVATIONS";
const FETCH_SURVEY_EFFICIENCY_OBSERVATIONS_OK =
  "skyportal/FETCH_SURVEY_EFFICIENCY_OBSERVATIONS_OK";

const SUBMIT_SURVEY_EFFICIENCY_OBSERVATIONS =
  "skyportal/SUBMIT_SURVEY_EFFICIENCY_OBSERVATIONS";

const DELETE_SURVEY_EFFICIENCY_OBSERVATIONS =
  "skyportal/DELETE_SURVEY_EFFICIENCY_OBSERVATIONS";

export const fetchSurveyEfficiencyObservations = (params = {}) =>
  API.GET(
    "/api/survey_efficiency/observations",
    FETCH_SURVEY_EFFICIENCY_OBSERVATIONS,
    params,
  );

export function submitSurveyEfficiencyObservations(
  id: number | string,
  data: Record<string, any> = {},
) {
  return API.GET(
    `/api/observation/simsurvey/${id}`,
    SUBMIT_SURVEY_EFFICIENCY_OBSERVATIONS,
    data,
  );
}

export function deleteSurveyEfficiencyObservations(id: number | string) {
  return API.DELETE(
    `/api/observation/simsurvey/${id}`,
    DELETE_SURVEY_EFFICIENCY_OBSERVATIONS,
  );
}

// Websocket message handler
messageHandler.add(
  (actionType: string, payload: any, dispatch: AppDispatch) => {
    if (actionType === REFRESH_SURVEY_EFFICIENCY_OBSERVATIONS) {
      dispatch(fetchSurveyEfficiencyObservations());
    }
  },
);

type SurveyEfficiencyObservationsState = Record<string, any>;

interface SurveyEfficiencyObservationsAction {
  type: string;
  data?: any;
}

const reducer = (
  state: SurveyEfficiencyObservationsState = {
    surveyEfficiencyObservations: [],
  },
  action: SurveyEfficiencyObservationsAction,
): SurveyEfficiencyObservationsState => {
  switch (action.type) {
    case FETCH_SURVEY_EFFICIENCY_OBSERVATIONS_OK: {
      const surveyEfficiencyObservations = action.data;
      return {
        ...state,
        surveyEfficiencyObservations,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("surveyEfficiencyObservations", reducer);
