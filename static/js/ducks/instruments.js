import * as API from "../API";
import store from "../store";

const FETCH_INSTRUMENTS = "skyportal/FETCH_INSTRUMENTS";
const FETCH_INSTRUMENTS_OK = "skyportal/FETCH_INSTRUMENTS_OK";

const fetchInstruments = () => API.GET("/api/instrument", FETCH_INSTRUMENTS);

const reducer = (state = { instrumentList: [] }, action) => {
  switch (action.type) {
    case FETCH_INSTRUMENTS_OK: {
      const instruments = action.data;
      return {
        ...state,
        instrumentList: instruments,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("instruments", reducer);

export default fetchInstruments;
