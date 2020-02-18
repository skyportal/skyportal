import * as API from '../API';
import store from '../store';


export const FETCH_SOURCES = 'skyportal/FETCH_SOURCES';
export const FETCH_SOURCES_OK = 'skyportal/FETCH_SOURCES_OK';
export const FETCH_SOURCES_FAIL = 'skyportal/FETCH_SOURCES_FAIL';


export function fetchSources(page=1) {
  return API.GET(`/api/sources?page=${page}`, FETCH_SOURCES);
}

export function submitSourceFilterParams(formData) {
  return API.POST(`/api/sources/filter`, FETCH_SOURCES, formData);
}


const initialState = {
  latest: null,
  pageNumber: 1,
  lastPage: false,
  totalMatches: 0,
  sourceNumberingStart: 0,
  sourceNumberingEnd: 0
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
      const { sources, pageNumber, lastPage, totalMatches, sourceNumberingStart,
        sourceNumberingEnd } = action.data;
      return {
        ...state,
        latest: sources,
        queryInProgress: false,
        pageNumber,
        lastPage,
        totalMatches,
        sourceNumberingStart,
        sourceNumberingEnd
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
