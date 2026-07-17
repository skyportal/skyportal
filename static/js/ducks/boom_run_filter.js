import * as API from "../API";
import store from "../store";
import { brokerFilterBase } from "./brokerFilterTarget";

export const RUN_BOOM_FILTER = "skyportal/RUN_BOOM_FILTER";
export const RUN_BOOM_FILTER_OK = "skyportal/RUN_BOOM_FILTER_OK";
export const RUN_BOOM_FILTER_ERROR = "skyportal/RUN_BOOM_FILTER_ERROR";
export const RUN_BOOM_FILTER_FAIL = "skyportal/RUN_BOOM_FILTER_FAIL";
export const BOOM_FILTER_CLEAR = "skyportal/BOOM_FILTER_CLEAR";

export function runBoomFilter({
  pipeline,
  selectedCollection,
  start_jd,
  end_jd,
  filter_id,
}) {
  return API.POST(`${brokerFilterBase()}/filter/test`, RUN_BOOM_FILTER, {
    pipeline,
    selectedCollection,
    start_jd,
    end_jd,
    filter_id,
  });
}

export function runBoomTestFilter({
  pipeline,
  selectedCollection,
  start_jd,
  end_jd,
  filter_id,
  sort_by,
  sort_order,
  limit,
  cursor = null,
}) {
  return API.POST(`${brokerFilterBase()}/filter/test`, RUN_BOOM_FILTER, {
    pipeline,
    selectedCollection,
    start_jd,
    end_jd,
    filter_id,
    sort_by,
    sort_order,
    limit,
    cursor,
  });
}

export function clearBoomFilter() {
  return {
    type: BOOM_FILTER_CLEAR,
  };
}

const reducer = (state = {}, action) => {
  switch (action.type) {
    case RUN_BOOM_FILTER_OK: {
      return action.data;
    }
    case RUN_BOOM_FILTER_FAIL:
    case RUN_BOOM_FILTER_ERROR:
    case BOOM_FILTER_CLEAR: {
      return {};
    }
    default:
      return state;
  }
};

store.injectReducer("query_result", reducer);
