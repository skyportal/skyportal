import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';

import * as Action from '../ducks/users';


const UserInfo = ({ route }) => {
  const dispatch = useDispatch();
  useEffect(() => {
    dispatch(Action.fetchUser(route.id));
  }, []);
  const users = useSelector((state) => state.users);
  const user_info = users[route.id];
  if (user_info === undefined) {
    return (
      <div>
        Loading...
      </div>
    );
  } else {
    const { created_at, username } = user_info;
    let acls = user_info.acls || [{ id: 'None' }];
    acls = acls.map((acl) => (acl.id));
    return (
      <div>
        <b>
          {username}
        </b>
        <ul>
          <li>
            <b>
created_at:
            </b>
            {' '}
            {created_at}
          </li>
          <li>
            <b>
acls:
            </b>
            {' '}
            {acls.join(', ')}
          </li>
        </ul>
      </div>
    );
  }
};
UserInfo.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string
  }).isRequired
};

export default UserInfo;
