import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_SHIFT = "skyportal/REFRESH_SHIFT";

const FETCH_SHIFT = "skyportal/FETCH_SHIFT";

const SUBMIT_SHIFT = "skyportal/SUBMIT_SHIFT";

const DELETE_SHIFT = "skyportal/DELETE_SHIFT";

const CURRENT_SHIFT = "skyportal/CURRENT_SHIFT";

const CURRENT_SHIFT_SELECTED_USERS = "skyportal/CURRENT_SHIFT_SELECTED_USERS";

export const fetchShift = (id) => API.GET(`/api/shifts/${id}`, FETCH_SHIFT);

export const submitShift = (run) => API.POST(`/api/shifts`, SUBMIT_SHIFT, run);

export function deleteShift(shiftID) {
  return API.DELETE(`/api/shifts/${shiftID}`, DELETE_SHIFT);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { shift } = getState();
  if (actionType === REFRESH_SHIFT) {
    const { shift_id } = payload;
    if (shift_id === shift?.id) {
      dispatch(fetchShift(shift_id));
    }
  }
});

const reducer = (state = { currentShift: {}, selectedUsers: [] }, action) => {
  switch (action.type) {
    case CURRENT_SHIFT: {
      const currentShift = action.data;
      return {
        ...state,
        currentShift,
      };
    }
    case CURRENT_SHIFT_SELECTED_USERS: {
      const selectedUsers = action.data;
      return {
        ...state,
        selectedUsers,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("shift", reducer);
