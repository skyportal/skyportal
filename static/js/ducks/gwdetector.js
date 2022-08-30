import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_GWDETECTOR = "skyportal/REFRESH_GWDETECTOR";

const FETCH_GWDETECTOR = "skyportal/FETCH_GWDETECTOR";
const FETCH_GWDETECTOR_OK = "skyportal/FETCH_GWDETECTOR_OK";

const SUBMIT_GWDETECTOR = "skyportal/SUBMIT_GWDETECTOR";

const CURRENT_GWDETECTORS_AND_MENU = "skyportal/CURRENT_GWDETECTORS_AND_MENU";

export const fetchGWDetector = (id) =>
  API.GET(`/api/gwdetector/${id}`, FETCH_GWDETECTOR);

export const submitGWDetector = (run) =>
  API.POST(`/api/gwdetector`, SUBMIT_GWDETECTOR, run);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { gwdetector } = getState();
  if (actionType === REFRESH_GWDETECTOR) {
    const { gwdetector_id } = payload;
    if (gwdetector_id === gwdetector?.id) {
      dispatch(fetchGWDetector(gwdetector_id));
    }
  }
});

const reducer = (
  state = {
    assignments: [],
    currentGWDetectors: null,
    currentGWDetectorMenu: "GWDetector List",
  },
  action
) => {
  switch (action.type) {
    case FETCH_GWDETECTOR_OK: {
      const gwdetector = action.data;
      return {
        ...state,
        ...gwdetector,
      };
    }
    case CURRENT_GWDETECTORS_AND_MENU: {
      const gwdetector = {};
      console.log(
        "action.data.currentGWDetectorMenu",
        action.data.currentGWDetectorMenu
      );
      gwdetector.currentGWDetectors = action.data.currentGWDetectors;
      gwdetector.currentGWDetectorMenu = action.data.currentGWDetectorMenu;
      return {
        ...state,
        ...gwdetector,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("gwdetector", reducer);
