import { connect } from 'react-redux';

import SearchBox from '../components/SearchBox';
import * as Action from '../actions';


const mapDispatchToProps = (dispatch, ownProps) => (
  {
    filterSources: formState => {
      formState['pageNumber'] = 1;
      console.log("searchBox formState upon clicking submit:", formState);
      return dispatch(Action.submitSourceFilterParams(formState));
    },
    fetchSources: formState => dispatch(
      Action.fetchSources()
    ),
    nextPage: (formState) => {
      formState['pageNumber'] = ownProps.pageNumber + 1;
      console.log("searchBox formState on clicking nextPage:", formState);
      return dispatch(Action.submitSourceFilterParams(formState));
    },
    previousPage: (formState) => {
      formState['pageNumber'] = ownProps.pageNumber - 1;
      return dispatch(Action.submitSourceFilterParams(formState));
    }
  }
);

export default connect(null, mapDispatchToProps)(SearchBox);
