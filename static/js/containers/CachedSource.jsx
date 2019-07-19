import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import Source from '../components/Source';
import * as Action from '../actions';


class CachedSource extends React.Component {
  componentDidMount() {
    if (!this.isCached()) {
      const { id } = this.props.route;
      this.props.dispatch(Action.fetchSource(id));
    }
  }

  isCached() {
    const loadedSource = this.props.source;
    const cachedSource = loadedSource ? loadedSource.id : null;
    const requestedSource = this.props.route.id;

    return requestedSource === cachedSource;
  }

  render() {
    if (this.props.loadError) {
      return (
        <div>
Could not retrieve requested source
        </div>
      );
    } else if (!this.isCached()) {
      return (
        <div>
          <span>
Loading...
          </span>
        </div>
      );
    } else {
      return (
        <Source
          updateScore={this.props.updateScore}
          {...this.props.source}
        />
      );
    }
  }
}

CachedSource.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string
  }).isRequired,
  dispatch: PropTypes.func.isRequired,
  source: PropTypes.shape({
    id: PropTypes.string
  }).isRequired,
  loadError: PropTypes.bool.isRequired,
  updateScore: PropTypes.func.isRequired
};

const mapStateToProps = (state, ownProps) => (
  {
    source: state.source,
    loadError: state.source.loadError
  }
);

const mapDispatchToProps = (dispatch, ownProps) => (
  {
    updateScore: (id, value) => dispatch(
      Action.updateScore({ source_id: id, value })
    ),
    dispatch
  }
);

export default connect(mapStateToProps, mapDispatchToProps)(CachedSource);
