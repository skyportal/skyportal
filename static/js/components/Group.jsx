import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';

import * as groupActions from '../ducks/group';
import * as groupsActions from '../ducks/groups';
import NewGroupUserForm from './NewGroupUserForm';
import styles from "./Group.css";


const Group = ({ route }) => {
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const group = useSelector((state) => state.group);

  useEffect(() => {
    dispatch(groupActions.fetchGroup(route.id));
  }, []);

  if (!group || group.id === undefined) {
    return (
      <div>
        Group not found
      </div>
    );
  }
  return (
    <div className={styles.group}>
      <b>
        Group Name:&nbsp;&nbsp;
      </b>
      {group.name}
      <ul>
        {
          group.users.map((user, idx) => (
            <li key={user.id}>
              <Link to={`/user/${user.id}`}>
                {user.username}
              </Link>&nbsp;&nbsp;
              {
                group.group_users.filter((group_user) => group_user.user_id === user.id)[0].admin &&
                (
                  <div style={{ display: "inline-block" }}>
                    <span className={styles.badge}>
                      Admin
                    </span>&nbsp;&nbsp;
                  </div>
                )
              }
              {
                (currentUser.roles.includes('Super admin') ||
                 currentUser.roles.includes('Group admin')) &&
                (
                  <input
                    type="submit"
                    onClick={() => dispatch(
                        groupsActions.deleteGroupUser(
                          { username: user.username,
                            group_id: group.id }
                        )
                    )}
                    value="Remove from group"
                  />
                )
              }
            </li>
          ))
        }
      </ul>
      {
        (currentUser.roles.includes('Super admin') ||
         currentUser.roles.includes('Group admin')) && <NewGroupUserForm group_id={group.id} />
      }
      <br />
      <br />
      <br />
      {
        (currentUser.roles.includes('Super admin') ||
         currentUser.roles.includes('Group admin')) &&
        (
          <input
            type="submit"
            onClick={() => dispatch(
                groupsActions.deleteGroup(group.id)
            )}
            value="Delete Group"
          />
        )
      }
    </div>
  );
};

Group.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string
  }).isRequired
};


export default Group;
