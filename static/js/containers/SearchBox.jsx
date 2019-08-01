import { connect } from 'react-redux';

import SearchBox from '../components/SearchBox';
import * as Actions from '../ducks/fetchSources';


const mapDispatchToProps = (dispatch, ownProps) => (
  {
    filterSources: formState => dispatch(
      Actions.submitSourceFilterParams(formState)
    ),
    fetchSources: formState => dispatch(
      Actions.fetchSources()
    ),
    nextPage: (formState) => {
      formState = { ...formState, pageNumber: ownProps.sources.pageNumber + 1 };
      return dispatch(Actions.submitSourceFilterParams(formState));
    },
    previousPage: (formState) => {
      formState = { ...formState, pageNumber: ownProps.sources.pageNumber - 1 };
      return dispatch(Actions.submitSourceFilterParams(formState));
    }
  }
);

export default connect(null, mapDispatchToProps)(SearchBox);
