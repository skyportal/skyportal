import * as API from "../API";
import store from "../store";

const FETCH_TELESCOPES = "skyportal/FETCH_TELESCOPES";
const FETCH_TELESCOPES_OK = "skyportal/FETCH_TELESCOPES_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchTelescopes = () =>
  API.GET("/api/telescope", FETCH_TELESCOPES);

const reducer = (state = { telescopeList: [] }, action) => {
  switch (action.type) {
    case FETCH_TELESCOPES_OK: {
      const telescopeList = action.data;
      return {
        ...state,
        telescopeList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("telescopes", reducer);
