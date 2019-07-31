import { connect } from 'react-redux';

import SearchBox from '../components/SearchBox';
import * as fetchSourcesActions from '../ducks/fetchSources';


const mapDispatchToProps = (dispatch, ownProps) => (
  {
    filterSources: formState => dispatch(
      fetchSourcesActions.submitSourceFilterParams(formState)
    ),
    fetchSources: formState => dispatch(
      fetchSourcesActions.fetchSources()
    ),
    nextPage: (formState) => {
      formState = { ...formState, pageNumber: ownProps.sources.pageNumber + 1 };
      return dispatch(fetchSourcesActions.submitSourceFilterParams(formState));
    },
    previousPage: (formState) => {
      formState = { ...formState, pageNumber: ownProps.sources.pageNumber - 1 };
      return dispatch(fetchSourcesActions.submitSourceFilterParams(formState));
    }
  }
);

export default connect(null, mapDispatchToProps)(SearchBox);
