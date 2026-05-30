import React from "react";
import { makeStyles } from "tss-react/mui";

// import * as archiveActions from "../ducks/archive";
// IMPORTANT: the file imported above needs to be added to the same codebase where the UI plugin will be overwritten.
//            It should add the `cross_match` key to the redux store, along with methods to populate that field.

// list of cross-match catalogs to hide
const hiddenCrossMatches = ["PS1_PSC"];

// map the cross-match catalog names to the colors to use for plotting them
const crossMatchesColors = {};

// map the fields names to display for each cross-match source to the actual field names
const crossMatchesLabels = {};

// max radius in arcseconds to use for cross-matching
const radius = 10.0;

const useStyles = makeStyles()(() => ({
  pluginContainer: {
    paddingTop: "0.5em",
    width: "100%",
    height: "100%",
  },
}));

function getCrossMatches(ra: number, dec: number, dispatch: any): any {
  // implement logic to fetch cross matches from the archive
  // and add them to the redux store's "cross_matches" key
  return null;
}

function getCrossMatchesTraces(
  crossMatches: any,
  refRA: number,
  refDec: number,
) {
  const traces: any[] = [];
  // implement logic to display cross matches on the centroid plot
  return traces;
}

interface CentroidPlotPluginsProps {
  crossMatches?: Record<string, any>;
  refRA: number;
  refDec: number;
}

const CentroidPlotPlugins = ({
  crossMatches = {},
  refRA,
  refDec,
}: CentroidPlotPluginsProps): any => {
  const { classes } = useStyles();
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

export default CentroidPlotPlugins;

export { getCrossMatches, getCrossMatchesTraces };
