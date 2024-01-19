import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_SHIFTS = "skyportal/FETCH_SHIFTS";
const FETCH_SHIFTS_OK = "skyportal/FETCH_SHIFTS_OK";

const REFRESH_SHIFTS = "skyportal/REFRESH_SHIFTS";

const ADD_SHIFT_USER = "skyportal/ADD_SHIFT_USER";

const UPDATE_SHIFT_USER = "skyportal/UPDATE_SHIFT_USER";

const DELETE_SHIFT_USER = "skyportal/DELETE_SHIFT_USER";

function datestringToDate(shiftList) {
  const newShiftList = [...shiftList];
  for (let i = 0; i < shiftList.length; i += 1) {
    newShiftList[i].start_date = new Date(`${shiftList[i].start_date}Z`);
    newShiftList[i].end_date = new Date(`${shiftList[i].end_date}Z`);
  }
  return newShiftList;
}

// eslint-disable-next-line import/prefer-default-export
export const fetchShifts = () => API.GET("/api/shifts", FETCH_SHIFTS);

export function addShiftUser({ userID, admin, shiftID }) {
  return API.POST(`/api/shifts/${shiftID}/users`, ADD_SHIFT_USER, {
    userID,
    admin,
    shiftID,
  });
}

export const updateShiftUser = ({
  userID,
  admin,
  needs_replacement,
  shiftID,
}) =>
  API.PATCH(`/api/shifts/${shiftID}/users/${userID}`, UPDATE_SHIFT_USER, {
    admin,
    needs_replacement,
  });

export function deleteShiftUser({ userID, shiftID }) {
  return API.DELETE(
    `/api/shifts/${shiftID}/users/${userID}`,
    DELETE_SHIFT_USER,
    { userID, shiftID },
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
      const shiftList = datestringToDate(action.data);
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
