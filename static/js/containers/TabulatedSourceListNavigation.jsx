import React from 'react';
import { connect } from 'react-redux';

import TabulatedSourceListNavigation from '../components/TabulatedSourceListNavigation';
import * as Action from '../actions';

const mapDispatchToProps = (dispatch, ownProps) => (
  {
    nextPage: (currentPage) => dispatch(
      Action.fetchSources(currentPage + 1)
    ),
    previousPage: (currentPage) => dispatch(
      Action.fetchSources(currentPage - 1)
    )
  }
);

export default connect(null, mapDispatchToProps)(TabulatedSourceListNavigation);
