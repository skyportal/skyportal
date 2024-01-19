import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_DEFAULT_OBSERVATION_PLANS =
  "skyportal/REFRESH_DEFAULT_OBSERVATION_PLANS";

const DELETE_DEFAULT_OBSERVATION_PLAN =
  "skyportal/DELETE_DEFAULT_OBSERVATION_PLAN";

const FETCH_DEFAULT_OBSERVATION_PLANS =
  "skyportal/FETCH_DEFAULT_OBSERVATION_PLANS";
const FETCH_DEFAULT_OBSERVATION_PLANS_OK =
  "skyportal/FETCH_DEFAULT_OBSERVATION_PLANS_OK";

const SUBMIT_DEFAULT_OBSERVATION_PLAN =
  "skyportal/SUBMIT_DEFAULT_OBSERVATION_PLAN";

export function deleteDefaultObservationPlan(id) {
  return API.DELETE(
    `/api/default_observation_plan/${id}`,
    DELETE_DEFAULT_OBSERVATION_PLAN,
  );
}

export const fetchDefaultObservationPlans = () =>
  API.GET("/api/default_observation_plan", FETCH_DEFAULT_OBSERVATION_PLANS);

export const submitDefaultObservationPlan = (default_plan) =>
  API.POST(
    `/api/default_observation_plan`,
    SUBMIT_DEFAULT_OBSERVATION_PLAN,
    default_plan,
  );

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_DEFAULT_OBSERVATION_PLANS) {
    dispatch(fetchDefaultObservationPlans());
  }
});

const reducer = (
  state = {
    defaultObservationPlanList: [],
  },
  action,
) => {
  switch (action.type) {
    case FETCH_DEFAULT_OBSERVATION_PLANS_OK: {
      const default_observation_plans = action.data;
      return {
        ...state,
        defaultObservationPlanList: default_observation_plans,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("default_observation_plans", reducer);
