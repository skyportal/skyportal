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
    )
  }
);

export default connect(null, mapDispatchToProps)(SearchBox);
