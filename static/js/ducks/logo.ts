import store from "../store";

const ROTATE_LOGO = "skyportal/ROTATE_LOGO";

export function rotateLogo() {
  return {
    type: ROTATE_LOGO,
  };
}

interface LogoState {
  rotateLogo: boolean;
}

interface LogoAction {
  type: string;
  [key: string]: any;
}

const reducer = (
  state: LogoState = { rotateLogo: false },
  action: LogoAction,
): LogoState => {
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
