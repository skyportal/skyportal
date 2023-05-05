import * as API from "../API";

const FETCH_MATCHING_SUMMARIES = "skyportal/FETCH_MATCHING_SUMMARIES";

// eslint-disable-next-line import/prefer-default-export
export function fetchSummaryQuery(formData) {
  return API.POST(`/api/summary_query`, FETCH_MATCHING_SUMMARIES, formData);
}
