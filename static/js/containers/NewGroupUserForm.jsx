import { connect } from 'react-redux';

import NewGroupUserForm from '../components/NewGroupUserForm';
import * as Action from '../actions';


const mapDispatchToProps = (dispatch, ownProps) => (
  {
    addGroupUser: (username, admin) => dispatch(
      Action.addGroupUser({ username, admin, group_id: ownProps.group_id })
    )
  }
);

export default connect(null, mapDispatchToProps)(NewGroupUserForm);
