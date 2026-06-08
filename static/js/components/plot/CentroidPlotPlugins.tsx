// import * as archiveActions from "../ducks/archive";
// IMPORTANT: the file imported above needs to be added to the same codebase where the UI plugin will be overwritten.
//            It should add the `cross_match` key to the redux store, along with methods to populate that field.

function getCrossMatches(_ra: number, _dec: number, _dispatch: any): any {
  // implement logic to fetch cross matches from the archive
  // and add them to the redux store's "cross_matches" key
  return null;
}

function getCrossMatchesTraces(
  _crossMatches: any,
  _refRA: number,
  _refDec: number,
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
