import { connect } from 'react-redux';

import TokenList from '../components/TokenList';
import * as Action from '../ducks/groups';


const mapDispatchToProps = (dispatch, ownProps) => (
  {
    deleteToken: tokenID => dispatch(
      Action.deleteToken(tokenID)
    )
  }
);

export default connect(null, mapDispatchToProps)(TokenList);
