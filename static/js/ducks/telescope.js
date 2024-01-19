import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_TELESCOPE = "skyportal/REFRESH_TELESCOPE";

const FETCH_TELESCOPE = "skyportal/FETCH_TELESCOPE";
const FETCH_TELESCOPE_OK = "skyportal/FETCH_TELESCOPE_OK";

const SUBMIT_TELESCOPE = "skyportal/SUBMIT_TELESCOPE";

const DELETE_TELESCOPE = "skyportal/DELETE_TELESCOPE";

const CURRENT_TELESCOPES_AND_MENU = "skyportal/CURRENT_TELESCOPES_AND_MENU";

export const fetchTelescope = (id) =>
  API.GET(`/api/telescope/${id}`, FETCH_TELESCOPE);

export const submitTelescope = (tele) =>
  API.POST(`/api/telescope`, SUBMIT_TELESCOPE, tele);

export function deleteTelescope(id) {
  return API.DELETE(`/api/telescope/${id}`, DELETE_TELESCOPE);
}

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

const reducer = (
  state = {
    assignments: [],
    currentTelescopes: null,
    currentTelescopeMenu: "Telescope List",
  },
  action,
) => {
  switch (action.type) {
    case FETCH_TELESCOPE_OK: {
      const telescope = action.data;
      return {
        ...state,
        ...telescope,
      };
    }
    case CURRENT_TELESCOPES_AND_MENU: {
      const telescope = {};
      telescope.currentTelescopes = action.data.currentTelescopes;
      telescope.currentTelescopeMenu = action.data.currentTelescopeMenu;
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
