import { connect } from 'react-redux';

import Plot from '../components/Plot';
import { FETCH_SOURCE_PLOT } from '../actions';
import * as API from '../API';

const fetchPlotData = url => (
  API.GET(url, FETCH_SOURCE_PLOT)
);

const PlotContainer = connect(null, { fetchPlotData })(Plot);
export default PlotContainer;
