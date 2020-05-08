import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { Link, useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';

import * as groupActions from '../ducks/group';
import * as groupsActions from '../ducks/groups';
import NewGroupUserForm from './NewGroupUserForm';

import styles from './Group.css';


const Group = () => {
  const dispatch = useDispatch();
  const [groupLoadError, setGroupLoadError] = useState("");

  const { id } = useParams();
  const loadedId = useSelector((state) => state.group.id);

  useEffect(() => {
    const fetchGroup = async () => {
      const data = await dispatch(groupActions.fetchGroup(id));
      if (data.status === "error") {
        setGroupLoadError(data.message);
      }
    };
    fetchGroup();
  }, [id, loadedId, dispatch]);

  const group = useSelector((state) => state.group);
  const currentUser = useSelector((state) => state.profile);

  if (groupLoadError) {
    return (
      <div>
        {groupLoadError}
      </div>
    );
  }

  if (group && group.users) {
    const isAdmin = (aUser, aGroup) => (
      aGroup.group_users && aGroup.group_users.filter(
        (group_user) => (group_user.user_id === aUser.id)
      )[0].admin
    );

    return (
      <div>
        <b>
          Group Name:&nbsp;&nbsp;
        </b>
        {group.name}
        <br />
        <ul>
          {
            group.users.map((user) => (
              <li key={user.id}>
                <Link to={`/user/${user.id}`}>
                  {user.username}
                </Link>
                &nbsp;&nbsp;
                {
                  isAdmin(user, group) &&
                  (
                    <div style={{ display: "inline-block" }}>
                      <span className={styles.badge}>
                        Admin
                      </span>
                      &nbsp;&nbsp;
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
  }
  return <div>Loading group</div>;
};

Group.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string
  }).isRequired
};


export default Group;
