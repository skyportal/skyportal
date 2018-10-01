import React from 'react';
import { connect } from 'react-redux';

import TabulatedSourceListNavigation from '../components/TabulatedSourceListNavigation';
import * as Action from '../actions';

const mapStateToProps = (state) => (
  {
    pageNumber: state.sources.pageNumber
  }
);

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

export default connect(mapStateToProps, mapDispatchToProps)(TabulatedSourceListNavigation);
