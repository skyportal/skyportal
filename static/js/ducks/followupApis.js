import * as API from "../API";

export const FETCH_FOLLOWUP_APIS = "FETCH_FOLLOWUP_APIS";

export const fetchFollowupApis = () =>
  API.GET("/api/internal/followup_apis", FETCH_FOLLOWUP_APIS);
