import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import * as fetchSourcesActions from '../ducks/fetchSources';

import SourceList from '../components/SourceList';
import UninitializedDBMessage from '../components/UninitializedDBMessage';


class SourceListContainer extends React.Component {
  componentDidMount() {
    if (!this.props.sources.latest) {
      this.props.dispatch(fetchSourcesActions.fetchSources());
    }
  }

  render() {
    if (this.props.sourcesTableEmpty) {
      return <UninitializedDBMessage />;
    }
    if (this.props.sources) {
      return <SourceList sources={this.props.sources} />;
    } else {
      return "Loading sources...";
    }
  }
}

SourceListContainer.propTypes = {
  dispatch: PropTypes.func.isRequired,
  sources: PropTypes.object,
  sourcesTableEmpty: PropTypes.bool
};

SourceListContainer.defaultProps = {
  sources: null,
  sourcesTableEmpty: false
};

const mapStateToProps = (state, ownProps) => (
  {
    sources: state.sources,
    sourcesTableEmpty: state.sysinfo.sources_table_empty
  }
);

export default connect(mapStateToProps)(SourceListContainer);
