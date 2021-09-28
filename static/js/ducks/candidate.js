import * as API from "../API";
import store from "../store";

const FETCH_CANDIDATE = "skyportal/FETCH_CANDIDATE";
const FETCH_CANDIDATE_OK = "skyportal/FETCH_CANDIDATE_OK";
const FETCH_CANDIDATE_FAIL = "skyportal/FETCH_CANDIDATE_FAIL";
const FETCH_CANDIDATE_ERROR = "skyportal/FETCH_CANDIDATE_ERROR";

// eslint-disable-next-line import/prefer-default-export
export const fetchCandidate = (id, how = FETCH_CANDIDATE) =>
  API.GET(`/api/candidates/${id}`, how);

const initialState = {
  candidate: null,
};

const reducer = (state = initialState, action) => {
  switch (action.type) {
    case FETCH_CANDIDATE_OK: {
      const candidate = action.data;
      return {
        ...state,
        ...candidate,
        loadError: "",
      };
    }
    case FETCH_CANDIDATE_ERROR:
      return {
        ...state,
        loadError: action.message,
      };
    case FETCH_CANDIDATE_FAIL:
      return {
        ...state,
        loadError: `Error while loading candidate: ${action.message}`,
      };
    default:
      return state;
  }
};

store.injectReducer("candidate", reducer);
