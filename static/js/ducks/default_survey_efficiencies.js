import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_DEFAULT_SURVEY_EFFICIENCIES =
  "skyportal/REFRESH_DEFAULT_SURVEY_EFFICIENCIES";

const DELETE_DEFAULT_SURVEY_EFFICIENCY =
  "skyportal/DELETE_DEFAULT_SURVEY_EFFICIENCY";

const FETCH_DEFAULT_SURVEY_EFFICIENCIES =
  "skyportal/FETCH_DEFAULT_SURVEY_EFFICIENCIES";
const FETCH_DEFAULT_SURVEY_EFFICIENCIES_OK =
  "skyportal/FETCH_DEFAULT_SURVEY_EFFICIENCIES_OK";

const SUBMIT_DEFAULT_SURVEY_EFFICIENCY =
  "skyportal/SUBMIT_DEFAULT_SURVEY_EFFICIENCY";

export function deleteDefaultSurveyEfficiency(id) {
  return API.DELETE(
    `/api/default_survey_efficiency/${id}`,
    DELETE_DEFAULT_SURVEY_EFFICIENCY,
  );
}

export const fetchDefaultSurveyEfficiencies = () =>
  API.GET("/api/default_survey_efficiency", FETCH_DEFAULT_SURVEY_EFFICIENCIES);

export const submitDefaultSurveyEfficiency = (default_survey_efficiency) =>
  API.POST(
    `/api/default_survey_efficiency`,
    SUBMIT_DEFAULT_SURVEY_EFFICIENCY,
    default_survey_efficiency,
  );

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_DEFAULT_SURVEY_EFFICIENCIES) {
    dispatch(fetchDefaultSurveyEfficiencies());
  }
});

const reducer = (
  state = {
    defaultSurveyEfficiencyList: [],
  },
  action,
) => {
  switch (action.type) {
    case FETCH_DEFAULT_SURVEY_EFFICIENCIES_OK: {
      const default_survey_efficiencies = action.data;
      return {
        ...state,
        defaultSurveyEfficiencyList: default_survey_efficiencies,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("default_survey_efficiencies", reducer);
