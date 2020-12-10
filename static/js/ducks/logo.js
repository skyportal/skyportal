import store from "../store";

const ROTATE_LOGO = "skyportal/ROTATE_LOGO";

// eslint-disable-next-line import/prefer-default-export
export function rotateLogo() {
  return {
    type: ROTATE_LOGO,
  };
}

const reducer = (state = { rotateLogo: false }, action) => {
  switch (action.type) {
    case ROTATE_LOGO: {
      return {
        ...state,
        rotateLogo: true,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("logo", reducer);
