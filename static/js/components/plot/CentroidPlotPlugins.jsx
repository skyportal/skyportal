import React from "react"; // eslint-disable-line no-unused-vars
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography"; // eslint-disable-line no-unused-vars

// import * as archiveActions from "../ducks/archive";
// IMPORTANT: the file imported above needs to be added to the same codebase where the UI plugin will be overwritten.
//            It should add the `cross_match` key to the redux store, along with methods to populate that field.

// list of cross-match catalogs to hide
const hiddenCrossMatches = ["PS1_PSC"]; // eslint-disable-line no-unused-vars

// map the cross-match catalog names to the colors to use for plotting them
const crossMatchesColors = {}; // eslint-disable-line no-unused-vars

// map the fields names to display for each cross-match source to the actual field names
const crossMatchesLabels = {}; // eslint-disable-line no-unused-vars

// max radius in arcseconds to use for cross-matching
const radius = 10.0; // eslint-disable-line no-unused-vars

const useStyles = makeStyles(() => ({
  pluginContainer: {
    paddingTop: "0.5em",
    width: "100%",
    height: "100%",
  },
}));

// eslint-disable-next-line no-unused-vars
function getCrossMatches(ra, dec, dispatch) {
  // implement logic to fetch cross matches from the archive
  // and add them to the redux store's "cross_matches" key
  return null;
}

// eslint-disable-next-line no-unused-vars
function getCrossMatchesTraces(crossMatches, refRA, refDec) {
  const traces = [];
  // implement logic to display cross matches on the centroid plot
  return traces;
}

const CentroidPlotPlugins = ({ crossMatches, refRA, refDec }) => {
  const classes = useStyles(); // eslint-disable-line no-unused-vars
  if (
    !crossMatches ||
    Object.keys(crossMatches).length === 0 ||
    !refRA ||
    !refDec
  ) {
    return null;
  }

  // Implement plugin to display information under the centroid plot

  return null;
};

CentroidPlotPlugins.propTypes = {
  crossMatches: PropTypes.shape({}),
  refRA: PropTypes.number.isRequired,
  refDec: PropTypes.number.isRequired,
};

CentroidPlotPlugins.defaultProps = {
  crossMatches: {},
};

export default CentroidPlotPlugins;

export { getCrossMatches, getCrossMatchesTraces };
