import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_SHIFTS = "skyportal/FETCH_SHIFTS";
const FETCH_SHIFTS_OK = "skyportal/FETCH_SHIFTS_OK";

const REFRESH_SHIFTS = "skyportal/REFRESH_SHIFTS";
const REFRESH_SHIFTS_OK = "skyportal/REFRESH_SHIFTS";

// eslint-disable-next-line import/prefer-default-export
export const fetchShifts = () => API.GET("/api/shift", FETCH_SHIFTS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { shiftList } = getState();
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
