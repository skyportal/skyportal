import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_SURVEY_EFFICIENCY_OBSERVATION_PLANS =
  "skyportal/REFRESH_SURVEY_EFFICIENCY_OBSERVATION_PLANS";

const FETCH_SURVEY_EFFICIENCY_OBSERVATION_PLANS =
  "skyportal/FETCH_SURVEY_EFFICIENCY_OBSERVATION_PLANS";
const FETCH_SURVEY_EFFICIENCY_OBSERVATION_PLANS_OK =
  "skyportal/FETCH_SURVEY_EFFICIENCY_OBSERVATION_PLANS_OK";

const SUBMIT_SURVEY_EFFICIENCY_OBSERVATION_PLAN =
  "skyportal/SUBMIT_SURVEY_EFFICIENCY_OBSERVATION_PLAN";

const DELETE_SURVEY_EFFICIENCY_OBSERVATION_PLAN =
  "skyportal/DELETE_SURVEY_EFFICIENCY_OBSERVATION_PLAN";

export const fetchSurveyEfficiencyObservationPlans = () =>
  API.GET(
    "/api/survey_efficiency/observation_plan",
    FETCH_SURVEY_EFFICIENCY_OBSERVATION_PLANS,
  );

export function submitSurveyEfficiencyObservationPlan(
  id: number | string,
  data: Record<string, any> = {},
) {
  return API.GET(
    `/api/observation_plan/${id}/simsurvey`,
    SUBMIT_SURVEY_EFFICIENCY_OBSERVATION_PLAN,
    data,
  );
}

export function deleteSurveyEfficiencyObservationPlan(id: number | string) {
  return API.DELETE(
    `/api/observation_plan/${id}/simsurvey`,
    DELETE_SURVEY_EFFICIENCY_OBSERVATION_PLAN,
  );
}

// Websocket message handler
messageHandler.add((actionType: any, payload: any, dispatch: any) => {
  if (actionType === REFRESH_SURVEY_EFFICIENCY_OBSERVATION_PLANS) {
    dispatch(fetchSurveyEfficiencyObservationPlans());
  }
});

const reducer = (
  state: Record<string, any> = { surveyEfficiencyObservationPlans: [] },
  action: { type: string; data?: any },
): Record<string, any> => {
  switch (action.type) {
    case FETCH_SURVEY_EFFICIENCY_OBSERVATION_PLANS_OK: {
      const surveyEfficiencyObservationPlans = action.data;
      return {
        ...state,
        surveyEfficiencyObservationPlans,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("surveyEfficiencyObservationPlans", reducer);
