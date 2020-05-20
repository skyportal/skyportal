import * as API from '../API';
import store from '../store';


export const FETCH_SOURCES = 'skyportal/FETCH_SOURCES';
export const FETCH_SOURCES_OK = 'skyportal/FETCH_SOURCES_OK';
export const FETCH_SOURCES_FAIL = 'skyportal/FETCH_SOURCES_FAIL';


export function fetchSources(filterParams={}) {
  if (!Object.keys(filterParams).includes("pageNumber")) {
    filterParams.pageNumber = 1;
  }
  const params = new URLSearchParams(filterParams);
  const queryString = params.toString();
  return API.GET(`/api/sources?${queryString}`, FETCH_SOURCES);
}


const initialState = {
  latest: null,
  pageNumber: 1,
  lastPage: false,
  totalMatches: 0,
  numberingStart: 0,
  numberingEnd: 0
};

const reducer = (state=initialState, action) => {
  switch (action.type) {
    case FETCH_SOURCES: {
      return {
        ...state,
        queryInProgress: (action.parameters.body.pageNumber === undefined)
      };
    }
    case FETCH_SOURCES_OK: {
      const { sources, pageNumber, lastPage, totalMatches, numberingStart,
        numberingEnd } = action.data;
      return {
        ...state,
        latest: sources,
        queryInProgress: false,
        pageNumber,
        lastPage,
        totalMatches,
        numberingStart,
        numberingEnd
      };
    }
    case FETCH_SOURCES_FAIL: {
      return {
        ...state,
        queryInProgress: false
      };
    }
    default:
      return state;
  }
};

store.injectReducer('sources', reducer);
