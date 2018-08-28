import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import Plot from '../components/Plot';
import * as Actions from '../actions';


class PlotContainer extends Component {
  constructor(props) {
    super(props);
    this.state = {
      error: false,
      fetchingPlotIDs: []
    };
  }

  componentWillMount() {
    this.fetchPlotDataIfNotCached();
  }

  componentWillReceiveProps() {
    this.fetchPlotDataIfNotCached();
  }

  needsFetching() {
    return (
      !this.props.plots.plotIDList.includes(this.props.url)
      && !this.state.fetchingPlotIDs.includes(this.props.url)
    );
  }

  fetchPlotDataIfNotCached() {
    if (this.needsFetching()) {
      this.props.dispatch(
        Actions.fetchPlotData(
          this.props.url,
          Actions.FETCH_SOURCE_PLOT
        )
      );
      const { fetchingPlotIDs } = this.state;
      this.setState(
        { fetchingPlotIDs: fetchingPlotIDs.concat([this.props.url]) }
      );
    }
    if (this.props.plots.plotData[this.props.url]
        && this.state.fetchingPlotIDs.includes(this.props.url)) {
      const fetchingPlotIDs = this.state.fetchingPlotIDs.slice();
      fetchingPlotIDs.splice(fetchingPlotIDs.indexOf(this.props.url), 1);
      this.setState({ fetchingPlotIDs });
    }
  }

  render() {
    return (
      <Plot
        plotData={this.props.plots.plotData[this.props.url]}
        error={this.state.error}
        className={this.props.className}
      />
    );
  }
}
PlotContainer.propTypes = {
  url: PropTypes.string.isRequired,
  className: PropTypes.string,
  plots: PropTypes.object.isRequired,
  dispatch: PropTypes.func.isRequired
};
PlotContainer.defaultProps = {
  className: ""
};

const mapStateToProps = (state, ownProps) => (
  {
    plots: state.plots
  }
);

PlotContainer = connect(mapStateToProps)(PlotContainer);
export default PlotContainer;
