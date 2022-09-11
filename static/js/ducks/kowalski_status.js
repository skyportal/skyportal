import * as API from "../API";
import store from "../store";

const FETCH_KOWALSKI_STATUS = "skyportal/FETCH_KOWALSKI_STATUS";
const FETCH_KOWALSKI_STATUS_OK = "skyportal/FETCH_KOWALSKI_STATUS_OK";

// eslint-disable-next-line import/prefer-default-export
export function fetchKowalskiStatus() {
  return API.GET("/api/internal/kowalski_status", FETCH_KOWALSKI_STATUS);
}

const reducer = (state = {}, action) => {
  switch (action.type) {
    case FETCH_KOWALSKI_STATUS_OK:
      return action.data;
    default:
      return state;
  }
};

store.injectReducer("kowalski_status", reducer);
