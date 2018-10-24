import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import * as Action from '../actions';

import SourceList from '../components/SourceList';


class SourceListContainer extends React.Component {
  componentDidMount() {
    if (!this.props.sources.latest) {
      this.props.dispatch(Action.fetchSources());
    }
  }

  render() {
    if (this.props.sources.latest) {
      return <SourceList sources={this.props.sources} />;
    } else {
      return "Loading sources...";
    }
  }
}

SourceListContainer.propTypes = {
  dispatch: PropTypes.func.isRequired,
  sources: PropTypes.object
};

SourceListContainer.defaultProps = {
  sources: null
};

const mapStateToProps = (state, ownProps) => (
  {
    sources: state.sources
  }
);

export default connect(mapStateToProps)(SourceListContainer);
