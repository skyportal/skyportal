import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

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
  const { allocation } = getState();
  if (actionType === REFRESH_ALLOCATION) {
    const { allocation_id } = payload;
    if (allocation_id === allocation?.id) {
      dispatch(fetchAllocation(allocation_id));
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
    case REFRESH_ALLOCATION_REQUEST_COMMENT: {
      const { followupRequest_id, followupRequest_comment } = action.payload;
      if (followupRequest_id) {
        const requestToUpdate = (state?.allocation?.requests || []).find(
          (request) => request?.id === followupRequest_id,
        );
        if (requestToUpdate) {
          requestToUpdate.comment = followupRequest_comment;
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
