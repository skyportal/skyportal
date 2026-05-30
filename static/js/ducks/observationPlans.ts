import * as API from "../API";
import store from "../store";

const EXISTING_PLAN_WITH_NAME = "skyportal/EXISTING_PLAN_WITH_NAME";

const FETCH_ALLOCATION_OBSERVATION_PLANS =
  "skyportal/FETCH_ALLOCATION_OBSERVATION_PLANS";
const FETCH_ALLOCATION_OBSERVATION_PLANS_OK =
  "skyportal/FETCH_ALLOCATION_OBSERVATION_PLANS_OK";

export const planWithSameNameExists = (planName: string) =>
  API.GET(
    `/api/observation_plan/plan_names?name=${planName}`,
    EXISTING_PLAN_WITH_NAME,
  );

export const fetchAllocationObservationPlans = (
  id: number | string,
  params: Record<string, any> = {},
) =>
  API.GET(
    `/api/allocation/observation_plans/${id}`,
    FETCH_ALLOCATION_OBSERVATION_PLANS,
    params,
  );

interface ObservationPlansAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (
  state: Record<string, any> = { observationPlanList: [] },
  action: ObservationPlansAction,
) => {
  switch (action.type) {
    case FETCH_ALLOCATION_OBSERVATION_PLANS_OK: {
      const { observation_plan_requests, totalMatches } = action.data;
      return {
        ...state,
        observation_plan_requests,
        totalMatches,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("observation_plans", reducer);
