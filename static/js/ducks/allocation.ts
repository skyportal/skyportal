import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch, RootState } from "../types/store";

const REFRESH_ALLOCATION = "skyportal/REFRESH_ALLOCATION";

const FETCH_ALLOCATION = "skyportal/FETCH_ALLOCATION";
const FETCH_ALLOCATION_OK = "skyportal/FETCH_ALLOCATION_OK";

const SUBMIT_ALLOCATION = "skyportal/SUBMIT_ALLOCATION";

const DELETE_ALLOCATION = "skyportal/DELETE_ALLOCATION";

const MODIFY_ALLOCATION = "skyportal/MODIFY_ALLOCATION";

const REFRESH_ALLOCATION_REQUEST_COMMENT =
  "skyportal/REFRESH_ALLOCATION_REQUEST_COMMENT";

const EDIT_FOLLOWUP_REQUEST_COMMENT = "skyportal/EDIT_FOLLOWUP_REQUEST_COMMENT";

export const fetchAllocation = (id: number | string, params = {}) =>
  API.GET(`/api/allocation/${id}`, FETCH_ALLOCATION, params);

export const modifyAllocation = (id: number | string, payload: any) =>
  API.PUT(`/api/allocation/${id}`, MODIFY_ALLOCATION, payload);

export const editFollowupRequestComment = (params: any, id: number | string) =>
  API.PUT(
    `/api/followup_request/${id}/comment`,
    EDIT_FOLLOWUP_REQUEST_COMMENT,
    params,
  );

export const submitAllocation = (payload: any) =>
  API.POST(`/api/allocation`, SUBMIT_ALLOCATION, payload);

export function deleteAllocation(allocationID: number | string) {
  return API.DELETE(`/api/allocation/${allocationID}`, DELETE_ALLOCATION);
}

// Websocket message handler
messageHandler.add(
  (
    actionType: string,
    payload: any,
    dispatch: AppDispatch,
    getState: () => RootState,
  ) => {
    const { allocation } = getState();
    if (actionType === REFRESH_ALLOCATION) {
      const { allocation_id } = payload;
      if (allocation_id === allocation?.id) {
        dispatch(fetchAllocation(allocation_id));
      }
    } else if (actionType === REFRESH_ALLOCATION_REQUEST_COMMENT) {
      dispatch({ type: actionType, payload });
    }
  },
);

type AllocationState = Record<string, any>;

interface AllocationAction {
  type: string;
  data?: any;
  payload?: any;
  [key: string]: any;
}

const reducer = (
  state: AllocationState = { assignments: [] },
  action: AllocationAction,
): AllocationState => {
  switch (action.type) {
    case FETCH_ALLOCATION_OK: {
      const { allocation, totalMatches } = action.data;
      return {
        ...state,
        allocation,
        totalMatches,
      };
    }
    case REFRESH_ALLOCATION_REQUEST_COMMENT: {
      const { followup_request_id, followup_request_comment } = action.payload;
      if (followup_request_id) {
        const requestToUpdate = (state?.["allocation"]?.requests || []).find(
          (request: any) => request?.id === followup_request_id,
        );
        if (requestToUpdate) {
          requestToUpdate.comment = followup_request_comment;
        }
      }
      return {
        ...state,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("allocation", reducer);
