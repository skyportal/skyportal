import * as API from '../API';

export const REFRESH_SOURCE = 'skyportal/REFRESH_SOURCE';

export const FETCH_LOADED_SOURCE = 'skyportal/FETCH_LOADED_SOURCE';
export const FETCH_LOADED_SOURCE_OK = 'skyportal/FETCH_LOADED_SOURCE_OK';
export const FETCH_LOADED_SOURCE_FAIL = 'skyportal/FETCH_LOADED_SOURCE_FAIL';

export function fetchSource(id) {
  return API.GET(`/api/sources/${id}`, FETCH_LOADED_SOURCE);
}

// Reducer for currently displayed source
export default function reducer(state={ source: null, loadError: false }, action) {
  switch (action.type) {
    case FETCH_LOADED_SOURCE_OK: {
      const source = action.data.sources;
      return {
        ...state,
        ...source,
        loadError: false
      };
    }
    case FETCH_LOADED_SOURCE_FAIL:
      return {
        ...state,
        loadError: true
      };
    default:
      return state;
  }
}
