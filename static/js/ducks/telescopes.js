import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_TELESCOPE = "skyportal/FETCH_TELESCOPE";
const FETCH_TELESCOPES = "skyportal/FETCH_TELESCOPES";
const FETCH_TELESCOPES_OK = "skyportal/FETCH_TELESCOPES_OK";

const SUBMIT_TELESCOPE = "skyportal/SUBMIT_TELESCOPE";
const DELETE_TELESCOPE = "skyportal/DELETE_TELESCOPE";

const CURRENT_TELESCOPES = "skyportal/CURRENT_TELESCOPES";

const REFRESH_TELESCOPE = "skyportal/REFRESH_TELESCOPE";
const REFRESH_TELESCOPES = "skyportal/REFRESH_TELESCOPES";

export const fetchTelescope = (id) =>
  API.GET(`/api/telescope/${id}`, FETCH_TELESCOPE);

export const fetchTelescopes = () =>
  API.GET("/api/telescope", FETCH_TELESCOPES);

export const submitTelescope = (tele) =>
  API.POST(`/api/telescope`, SUBMIT_TELESCOPE, tele);

export function deleteTelescope(id) {
  return API.DELETE(`/api/telescope/${id}`, DELETE_TELESCOPE);
}

messageHandler.add((actionType, payload, dispatch, getState) => {
  if (actionType === REFRESH_TELESCOPE) {
    const { telescope } = getState();
    const { telescope_id } = payload;
    if (telescope_id === telescope?.id) {
      dispatch(fetchTelescope(telescope_id));
    }
  }
  if (actionType === REFRESH_TELESCOPES) {
    dispatch(fetchTelescopes());
  }
});

const reducer = (
  state = {
    telescopeList: [],
    currentTelescopes: [],
    loading: true,
  },
  action,
) => {
  switch (action.type) {
    case FETCH_TELESCOPES_OK: {
      const telescopeList = action.data;
      return {
        ...state,
        telescopeList,
        loading: false,
      };
    }
    case CURRENT_TELESCOPES: {
      const { currentTelescopes } = action.data;
      return {
        ...state,
        currentTelescopes,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("telescopes", reducer);
