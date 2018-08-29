import { connect } from 'react-redux';

import TokenList from '../components/TokenList';
import * as Action from '../actions';


const mapDispatchToProps = (dispatch, ownProps) => (
  {
    deleteToken: tokenID => dispatch(
      Action.deleteToken(tokenID)
    )
  }
);

export default connect(null, mapDispatchToProps)(TokenList);
