import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

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

// eslint-disable-next-line import/prefer-default-export
export const fetchSurveyEfficiencyObservations = (params = {}) =>
  API.GET(
    "/api/survey_efficiency/observations",
    FETCH_SURVEY_EFFICIENCY_OBSERVATIONS,
    params,
  );

export function submitSurveyEfficiencyObservations(id, data = {}) {
  return API.GET(
    `/api/observation/simsurvey/${id}`,
    SUBMIT_SURVEY_EFFICIENCY_OBSERVATIONS,
    data,
  );
}

export function deleteSurveyEfficiencyObservations(id) {
  return API.DELETE(
    `/api/observation/simsurvey/${id}`,
    DELETE_SURVEY_EFFICIENCY_OBSERVATIONS,
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_SURVEY_EFFICIENCY_OBSERVATIONS) {
    dispatch(fetchSurveyEfficiencyObservations());
  }
});

const reducer = (state = { surveyEfficiencyObservations: [] }, action) => {
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
