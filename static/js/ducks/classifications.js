import store from "../store";

const SET_TAXONOMY = "skyportal/SET_TAXONOMY";
const SET_SCALE_PROBABILITIES = "skyportal/SET_SCALE_PROBABILITIES";

// eslint-disable-next-line import/prefer-default-export
export const setTaxonomy = (taxonomy) => ({
  type: SET_TAXONOMY,
  taxonomy,
});

// eslint-disable-next-line import/prefer-default-export
export const setScaleProbabilities = (scaleProbabilities) => ({
  type: SET_SCALE_PROBABILITIES,
  scaleProbabilities,
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
    case SET_SCALE_PROBABILITIES: {
      const { scaleProbabilities } = action;
      return {
        ...state,
        scaleProbabilities,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("classifications", reducer);
