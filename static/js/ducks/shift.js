import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_SHIFT = "skyportal/REFRESH_SHIFT";

const FETCH_SHIFT = "skyportal/FETCH_SHIFT";

const SUBMIT_SHIFT = "skyportal/SUBMIT_SHIFT";

const DELETE_SHIFT = "skyportal/DELETE_SHIFT";

const CURRENT_SHIFT = "skyportal/CURRENT_SHIFT";

const CURRENT_SHIFT_SELECTED_USERS = "skyportal/CURRENT_SHIFT_SELECTED_USERS";

const FETCH_SHIFT_SUMMARY = "skyportal/FETCH_SHIFT_SUMMARY";

const FETCH_SHIFT_SUMMARY_OK = "skyportal/FETCH_SHIFT_SUMMARY_OK";

export const fetchShift = (id) => API.GET(`/api/shifts/${id}`, FETCH_SHIFT);

export const submitShift = (run) => API.POST(`/api/shifts`, SUBMIT_SHIFT, run);

export function deleteShift(shiftID) {
  return API.DELETE(`/api/shifts/${shiftID}`, DELETE_SHIFT);
}

export function getShiftsSummary({ shiftID, startDate, endDate }) {
  let data = null;
  let url = `/api/shifts/summary`;
  if (startDate && endDate) {
    data = { startDate, endDate };
  } else if (shiftID) {
    url = `/api/shifts/summary/${shiftID}`;
  }
  return API.GET(url, FETCH_SHIFT_SUMMARY, data);
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

const reducer = (
  state = { currentShift: {}, selectedUsers: [], shiftsSummary: [] },
  action
) => {
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
    case FETCH_SHIFT_SUMMARY_OK: {
      const shiftsSummary = action.data;
      return {
        ...state,
        shiftsSummary,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("shift", reducer);
