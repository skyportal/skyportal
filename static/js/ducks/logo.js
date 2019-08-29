export const ROTATE_LOGO = 'skyportal/ROTATE_LOGO';

export function rotateLogo() {
  return {
    type: ROTATE_LOGO
  };
}

export default function reducer(state={ rotateLogo: false }, action) {
  switch (action.type) {
    case ROTATE_LOGO: {
      return {
        ...state,
        rotateLogo: true
      };
    }
    default:
      return state;
  }
}
