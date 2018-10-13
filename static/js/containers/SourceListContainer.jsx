import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import * as Action from '../actions';

import SourceList from '../components/SourceList';


class SourceListContainer extends React.Component {
  componentDidMount() {
    if (!this.props.sources) {
      this.props.dispatch(Action.fetchSources());
    }
  }

  render() {
    if (this.props.sources) {
      return (
        <SourceList
          sources={this.props.sources}
          pageNumber={this.props.pageNumber}
          lastPage={this.props.lastPage}
        />
      );
    } else {
      return "Loading sources...";
    }
  }
}

SourceListContainer.propTypes = {
  dispatch: PropTypes.func.isRequired,
  sources: PropTypes.arrayOf(PropTypes.object),
  pageNumber: PropTypes.number,
  lastPage: PropTypes.bool
};

SourceListContainer.defaultProps = {
  sources: null,
  pageNumber: 1,
  lastPage: false
};

const mapStateToProps = (state, ownProps) => (
  {
    sources: state.sources.latest,
    pageNumber: state.sources.pageNumber,
    lastPage: state.sources.lastPage
  }
);

export default connect(mapStateToProps)(SourceListContainer);
