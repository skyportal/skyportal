import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import * as Action from '../ducks/user';
import UserInfoComponent from '../components/UserInfo';


class UserInfo extends React.Component {
  componentDidMount() {
    const { route, fetchUser } = this.props;
    fetchUser(route.id);
  }

  render() {
    const { route, users } = this.props;
    const { id } = route;
    const user_info = users[id];

    if (user_info === undefined) {
      return (
        <div>
          Loading...
        </div>
      );
    } else {
      let acls = user_info.acls || [{ id: 'None' }];
      acls = acls.map(acl => (acl.id));
      return (
        <UserInfoComponent
          id={id}
          username={user_info.username}
          created_at={user_info.created_at}
          acls={acls}
        />
      );
    }
  }
}
UserInfo.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string
  }).isRequired,
  users: PropTypes.shape({
    id: PropTypes.string
  }).isRequired,
  fetchUser: PropTypes.func.isRequired
};

const mapDispatchToProps = (dispatch, ownProps) => (
  {
    fetchUser: id => dispatch(
      Action.fetchUser(id)
    )
  }
);

const mapStateToProps = (state, ownProps) => (
  {
    users: state.users
  }
);

export default connect(mapStateToProps, mapDispatchToProps)(UserInfo);
