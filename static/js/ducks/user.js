import * as API from '../API';


export const FETCH_USER = 'skyportal/FETCH_USER';
export const FETCH_USER_OK = 'skyportal/FETCH_USER_OK';

export function fetchUser(id) {
  return API.GET(`/api/user/${id}`, FETCH_USER);
}

export default function reducer(state={}, action) {
  switch (action.type) {
    case FETCH_USER_OK: {
      const { id, ...user_info } = action.data.user;
      return {
        ...state,
        [id]: user_info
      };
    }
    default:
      return state;
  }
}
