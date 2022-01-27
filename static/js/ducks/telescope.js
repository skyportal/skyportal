import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_TELESCOPE = "skyportal/REFRESH_TELESCOPE";

const FETCH_TELESCOPE = "skyportal/FETCH_TELESCOPE";
const FETCH_TELESCOPE_OK = "skyportal/FETCH_TELESCOPE_OK";

const SUBMIT_TELESCOPE = "skyportal/SUBMIT_TELESCOPE";

export const fetchTelescope = (id) =>
  API.GET(`/api/telescope/${id}`, FETCH_TELESCOPE);

export const submitTelescope = (run) =>
  API.POST(`/api/telescope`, SUBMIT_TELESCOPE, run);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { telescope } = getState();
  if (actionType === REFRESH_TELESCOPE) {
    const { telescope_id } = payload;
    if (telescope_id === telescope?.id) {
      dispatch(fetchTelescope(telescope_id));
    }
  }
});

const reducer = (state = { assignments: [] }, action) => {
  switch (action.type) {
    case FETCH_TELESCOPE_OK: {
      const telescope = action.data;
      return {
        ...state,
        ...telescope,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("telescope", reducer);
