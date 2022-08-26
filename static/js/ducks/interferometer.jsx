import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_INTERFEROMETER = "skyportal/REFRESH_INTERFEROMETER";

const FETCH_INTERFEROMETER = "skyportal/FETCH_INTERFEROMETER";
const FETCH_INTERFEROMETER_OK = "skyportal/FETCH_INTERFEROMETER_OK";

const SUBMIT_INTERFEROMETER = "skyportal/SUBMIT_INTERFEROMETER";

const CURRENT_INTERFEROMETERS_AND_MENU =
  "skyportal/CURRENT_INTERFEROMETERS_AND_MENU";

export const fetchInterferometer = (id) =>
  API.GET(`/api/interferometer/${id}`, FETCH_INTERFEROMETER);

export const submitInterferometer = (run) =>
  API.POST(`/api/interferometer`, SUBMIT_INTERFEROMETER, run);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { interferometer } = getState();
  if (actionType === REFRESH_INTERFEROMETER) {
    const { interferometer_id } = payload;
    if (interferometer_id === interferometer?.id) {
      dispatch(fetchInterferometer(interferometer_id));
    }
  }
});

const reducer = (
  state = {
    assignments: [],
    currentInterferometers: null,
    currentInterferometerMenu: "Interferometer List",
  },
  action
) => {
  switch (action.type) {
    case FETCH_INTERFEROMETER_OK: {
      const interferometer = action.data;
      return {
        ...state,
        ...interferometer,
      };
    }
    case CURRENT_INTERFEROMETERS_AND_MENU: {
      const interferometer = {};
      console.log(
        "action.data.currentInterferometerMenu",
        action.data.currentInterferometerMenu
      );
      interferometer.currentInterferometers =
        action.data.currentInterferometers;
      interferometer.currentInterferometerMenu =
        action.data.currentInterferometerMenu;
      return {
        ...state,
        ...interferometer,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("interferometer", reducer);
