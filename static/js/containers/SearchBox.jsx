import { connect } from 'react-redux';

import SearchBox from '../components/SearchBox';
import * as Action from '../actions';


const mapDispatchToProps = (dispatch, ownProps) => (
  {
    filterSources: formState => dispatch(
      Action.submitSourceFilterParams(formState)
    ),
    fetchSources: formState => dispatch(
      Action.fetchSources()
    ),
    nextPage: (formState) => {
      formState = { ...formState, pageNumber: ownProps.sources.pageNumber + 1 };
      return dispatch(Action.submitSourceFilterParams(formState));
    },
    previousPage: (formState) => {
      formState = { ...formState, pageNumber: ownProps.sources.pageNumber - 1 };
      return dispatch(Action.submitSourceFilterParams(formState));
    }
  }
);

export default connect(null, mapDispatchToProps)(SearchBox);
