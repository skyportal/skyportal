import * as API from "../API";

const EXISTING_PLAN_WITH_NAME = "skyportal/EXISTING_PLAN_WITH_NAME";

const planWithSameNameExists = (planName) =>
  API.GET(
    `/api/observation_plan/plan_names?name=${planName}`,
    EXISTING_PLAN_WITH_NAME,
  );

export default planWithSameNameExists;
