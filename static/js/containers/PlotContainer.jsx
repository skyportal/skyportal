import React from 'react';
import { connect } from 'react-redux';

import Plot from '../components/Plot';
import { RECEIVE_SOURCE_PLOT } from '../actions';
import * as API from '../API';

let fetchPlotData = (url) => (
  API.GET(url, RECEIVE_SOURCE_PLOT)
);

const PlotContainer = connect(null, {fetchPlotData})(Plot);
export default PlotContainer;
