import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_SHIFTS = "skyportal/REFRESH_SHIFTS";

const FETCH_SHIFTS = "skyportal/FETCH_SHIFTS";
const FETCH_SHIFTS_OK = "skyportal/FETCH_SHIFTS_OK";
const FETCH_SHIFTS_ERROR = "skyportal/FETCH_SHIFTS_ERROR";
const FETCH_SHIFTS_FAIL = "skyportal/FETCH_SHIFTS_FAIL";

// eslint-disable-next-line import/prefer-default-export
/*export function fetchShifts(id) {
  return API.GET(`/api/shifts/${id}`, FETCH_SHIFTS);
}*/

export function fetchShifts() {
  return API.GET(`/api/shifts`, FETCH_SHIFTS);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { shifts } = getState();

  if (actionType === REFRESH_SHIFTS) {
    const loaded_shifts_id = shifts ? shifts.id : null;

    if (loaded_shifts_id === payload.shifts_id) {
      dispatch(fetchGroup(loaded_shifts_id));
    }
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_SHIFTS_OK: {
      return action.data;
    }
    case FETCH_SHIFTS_FAIL:
    case FETCH_SHIFTS_ERROR: {
      return null;
    }
    default:
      return state;
  }
};

store.injectReducer("shifts", reducer);