import store from "../store";

const SET_TAXONOMY = "skyportal/SET_TAXONOMY";
const SET_NORMALIZE_PROBABILITIES = "skyportal/SET_NORMALIZE_PROBABILITIES";

// eslint-disable-next-line import/prefer-default-export
export const setTaxonomy = (taxonomy) => ({
  type: SET_TAXONOMY,
  taxonomy,
});

// eslint-disable-next-line import/prefer-default-export
export const setNormalizeProbabilities = (normalizeProbabilities) => ({
  type: SET_NORMALIZE_PROBABILITIES,
  normalizeProbabilities,
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
    case SET_NORMALIZE_PROBABILITIES: {
      const { normalizeProbabilities } = action;
      return {
        ...state,
        normalizeProbabilities,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("classifications", reducer);
