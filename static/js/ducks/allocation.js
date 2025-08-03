import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import { FETCH_FOLLOWUP_REQUEST_OK } from "./followupRequests";

const REFRESH_ALLOCATION = "skyportal/REFRESH_ALLOCATION";

const FETCH_ALLOCATION = "skyportal/FETCH_ALLOCATION";
const FETCH_ALLOCATION_OK = "skyportal/FETCH_ALLOCATION_OK";

const SUBMIT_ALLOCATION = "skyportal/SUBMIT_ALLOCATION";

const DELETE_ALLOCATION = "skyportal/DELETE_ALLOCATION";

const MODIFY_ALLOCATION = "skyportal/MODIFY_ALLOCATION";

const REFRESH_ALLOCATION_REQUEST_COMMENT =
  "skyportal/REFRESH_ALLOCATION_REQUEST_COMMENT";

const EDIT_FOLLOWUP_REQUEST_COMMENT = "skyportal/EDIT_FOLLOWUP_REQUEST_COMMENT";

export const fetchAllocation = (id, params = {}) =>
  API.GET(`/api/allocation/${id}`, FETCH_ALLOCATION, params);

export const modifyAllocation = (id, run) =>
  API.PUT(`/api/allocation/${id}`, MODIFY_ALLOCATION, run);

export const editFollowupRequestComment = (params, id) =>
  API.PUT(
    `/api/followup_request/${id}/comment`,
    EDIT_FOLLOWUP_REQUEST_COMMENT,
    params,
  );

export const submitAllocation = (run) =>
  API.POST(`/api/allocation`, SUBMIT_ALLOCATION, run);

export function deleteAllocation(allocationID) {
  return API.DELETE(`/api/allocation/${allocationID}`, DELETE_ALLOCATION);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  if (actionType === REFRESH_ALLOCATION) {
    const { allocation } = getState();
    if (
      payload?.allocation_id &&
      payload.allocation_id === allocation?.allocation?.id
    ) {
      dispatch(fetchAllocation(payload?.allocation_id));
    }
  } else if (actionType === REFRESH_ALLOCATION_REQUEST_COMMENT) {
    dispatch({ type: actionType, payload });
  }
});

const reducer = (state = { assignments: [] }, action) => {
  switch (action.type) {
    case FETCH_ALLOCATION_OK: {
      const { allocation, totalMatches } = action.data;
      return {
        ...state,
        allocation,
        totalMatches,
      };
    }
    case FETCH_FOLLOWUP_REQUEST_OK: {
      const followupRequest = action.data;
      if (
        !state?.allocation ||
        followupRequest?.allocation_id !== state.allocation.id
      )
        return state;

      const updatedRequests = state?.allocation?.requests?.map((request) =>
        request.id === followupRequest.id ? followupRequest : request,
      );
      return {
        ...state,
        allocation: {
          ...state.allocation,
          requests: !state.allocation.requests?.length
            ? [followupRequest]
            : updatedRequests,
        },
      };
    }
    case REFRESH_ALLOCATION_REQUEST_COMMENT: {
      const { followup_request_id, followup_request_comment } = action.payload;
      if (followup_request_id) {
        const requestToUpdate = (state?.allocation?.requests || []).find(
          (request) => request?.id === followup_request_id,
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
