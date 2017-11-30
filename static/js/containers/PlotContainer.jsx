import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import Plot from '../components/Plot';
import { FETCH_SOURCE_PLOT } from '../actions';
import * as API from '../API';


class PlotContainer extends Component {
  async componentWillMount() {
    if (!this.props.plots.plotIDList.includes(this.props.url)) {
      // emit new action to fetch data
      const plotData = await this.props.fetchPlotData(this.props.url);
    } else {
      plotData = this.props.plots.plotData[this.props.url];
    }
    // how to handle error status?
    if (plotData) {
      this.setState({ plotData, error: false });
    } else {
      this.setState({ error: true });
    }
  }

  render() {
    return <Plot
             plotData={plotData}
             error={error}
           />;
  }
}

const mapStateToProps = (state, ownProps) => (
  {
    plots: state.plots
  }
);

const fetchPlotData = url => (
  API.GET(url, FETCH_SOURCE_PLOT)
);

const PlotContainer = connect(mapStateToProps, { fetchPlotData })(PlotContainer);
export default PlotContainer;
