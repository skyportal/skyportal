import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_SHIFTS = "skyportal/FETCH_SHIFTS";
const FETCH_SHIFTS_OK = "skyportal/FETCH_SHIFTS_OK";

const REFRESH_SHIFTS = "skyportal/REFRESH_SHIFTS";

const ADD_SHIFT_USER = "skyportal/ADD_SHIFT_USER";

const UPDATE_SHIFT_USER = "skyportal/UPDATE_SHIFT_USER";

const DELETE_SHIFT_USER = "skyportal/DELETE_SHIFT_USER";

// eslint-disable-next-line import/prefer-default-export
export const fetchShifts = () => API.GET("/api/shifts", FETCH_SHIFTS);

export function addShiftUser({ userID, admin, shift_id }) {
  return API.POST(`/api/shifts/${shift_id}/users`, ADD_SHIFT_USER, {
    userID,
    admin,
    shift_id,
  });
}

export const updateShiftUser = (shiftID, params) =>
  API.PATCH(`/api/shifts/${shiftID}/users`, UPDATE_SHIFT_USER, params);

export function deleteShiftUser({ userID, shift_id }) {
  console.log(userID, shift_id);
  return API.DELETE(
    `/api/shifts/${shift_id}/users/${userID}`,
    DELETE_SHIFT_USER,
    { userID, shift_id }
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_SHIFTS) {
    dispatch(fetchShifts());
  }
});

const reducer = (state = { shiftList: [] }, action) => {
  switch (action.type) {
    case FETCH_SHIFTS_OK: {
      const shiftList = action.data;
      return {
        ...state,
        shiftList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("shifts", reducer);
