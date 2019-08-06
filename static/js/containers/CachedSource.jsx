import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import Source from '../components/Source';
import * as Action from '../ducks/source';


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
      return <Source {...this.props.source} />;
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
  loadError: PropTypes.bool.isRequired
};

const mapStateToProps = (state, ownProps) => (
  {
    source: state.source,
    loadError: state.source.loadError
  }
);

export default connect(mapStateToProps)(CachedSource);
