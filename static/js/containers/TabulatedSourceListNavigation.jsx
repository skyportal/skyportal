import { connect } from 'react-redux';

import TabulatedSourceListNavigation from '../components/TabulatedSourceListNavigation';
import * as Action from '../actions';


const mapDispatchToProps = (dispatch, ownProps) => (
  {
    getNextPage: (currentPage) => dispatch(
      Action.fetchSources(currentPage + 1)
    ),
    getPreviousPage: (currentPage) => dispatch(
      Action.fetchSources(currentPage - 1)
    ),
  }
);

export default connect(null, mapDispatchToProps)(TabulatedSourceListNavigation);
