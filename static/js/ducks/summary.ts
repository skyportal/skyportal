import * as API from "../API";

const FETCH_MATCHING_SUMMARIES = "skyportal/FETCH_MATCHING_SUMMARIES";

export function fetchSummaryQuery(formData: any) {
  return API.POST(`/api/summary_query`, FETCH_MATCHING_SUMMARIES, formData);
}
