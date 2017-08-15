import React from 'react';
import { connect } from 'react-redux';

import Source from '../components/Source';
import * as Action from '../actions.js';


class CachedSource extends React.Component {
  componentDidMount() {
    if (!this.isCached()) {
      let id = this.props.route.id;
      this.props.dispatch(Action.fetchSource(id));
      console.log(this.props.source);
    }
  }

  isCached() {
    let loadedSource = this.props.source;
    let cachedSource = loadedSource ? loadedSource.id : null;
    let requestedSource = this.props.route.id;

    return requestedSource == cachedSource;
  }

  render = () => {
    if (this.props.loadError) {
      return <div>Could not retrieve requested source</div>
    } else {
      if (!this.isCached()) {
        return <div><span>Loading...</span></div>
      } else {
        return <Source {...this.props.source}/>
      }
    }
  }
}

const mapStateToProps = (state, ownProps) => (
  {
    source: state.source,
    loadError: state.source.loadError
  }
)

export default connect(mapStateToProps)(CachedSource);
