import * as API from '../API';


export const FETCH_GROUPS = 'skyportal/FETCH_GROUPS';
export const FETCH_GROUPS_OK = 'skyportal/FETCH_GROUPS_OK';

export function fetchGroups() {
  return API.GET('/api/groups', FETCH_GROUPS);
}

export default function reducer(state={ latest: [], all: null }, action) {
  switch (action.type) {
    case FETCH_GROUPS_OK: {
      const { user_groups, all_groups } = action.data;
      return {
        ...state,
        latest: user_groups,
        all: all_groups
      };
    }
    default:
      return state;
  }
}
