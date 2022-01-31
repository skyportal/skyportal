import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_SHIFT = "skyportal/REFRESH_SHIFT";

const FETCH_SHIFT = "skyportal/FETCH_SHIFT";
const FETCH_SHIFT_OK = "skyportal/FETCH_SHIFT_OK";

const SUBMIT_SHIFT = "skyportal/SUBMIT_SHIFT";

export const fetchShift = (id) => API.GET(`/api/shift/${id}`, FETCH_SHIFT);

export const submitShift = (run) => API.POST(`/api/shift`, SUBMIT_SHIFT, run);

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

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_SHIFT_OK: {
      const shift = action.data;
      return {
        ...state,
        ...shift,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("shift", reducer);
