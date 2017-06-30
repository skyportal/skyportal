import React from 'react';
import { connect } from 'react-redux';

import Plot from '../components/Plot';
import { API, RECEIVE_SOURCE_PLOT } from '../actions.js';

let fetchPlotData = (url) => (
  (dispatch) => {
    return API(url, RECEIVE_SOURCE_PLOT)(dispatch);
  }
)

const PlotContainer = connect(null, {fetchPlotData})(Plot);
export default PlotContainer;
