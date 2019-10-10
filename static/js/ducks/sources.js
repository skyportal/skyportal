import * as API from '../API';


export const FETCH_SOURCES = 'skyportal/FETCH_SOURCES';
export const FETCH_SOURCES_OK = 'skyportal/FETCH_SOURCES_OK';

export function fetchSources(page=1) {
  return API.GET(`/api/sources?page=${page}`, FETCH_SOURCES);
}

export function submitSourceFilterParams(formData) {
  return API.POST(`/api/sources/filter`, FETCH_SOURCES, formData);
}

export default function reducer(state={ latest: null,
  pageNumber: 1,
  lastPage: false,
  totalMatches: null,
  sourceNumberingStart: null,
  sourcesNumberingEnd: null },
action) {
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
    default:
      return state;
  }
}
