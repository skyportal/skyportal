import store from "../store";

const SET_TAXONOMY = "skyportal/SET_TAXONOMY";

// eslint-disable-next-line import/prefer-default-export
export const setTaxonomy = (taxonomy) => ({
  type: SET_TAXONOMY,
  taxonomy,
});

const reducer = (state = { rotateLogo: false }, action) => {
  switch (action.type) {
    case SET_TAXONOMY: {
      const { taxonomy } = action;
      return {
        ...state,
        taxonomy,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("classifications", reducer);
