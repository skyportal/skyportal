import * as API from '../API';
import store from '../store';

export const FETCH_USER = 'skyportal/FETCH_USER';
export const FETCH_USER_OK = 'skyportal/FETCH_USER_OK';

export function fetchUser(id) {
  return API.GET(`/api/user/${id}`, FETCH_USER);
}

const reducer = (state={}, action) => {
  switch (action.type) {
    case FETCH_USER_OK: {
      const { id, ...user_info } = action.data;
      return {
        ...state,
        [id]: user_info
      };
    }
    default:
      return state;
  }
};

store.injectReducer('users', reducer);
