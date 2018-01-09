import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';

import NewGroupUserForm from '../containers/NewGroupUserForm';
import styles from "./Group.css";


const Group = ({ name, id, users, currentUser }) => {
  if (id === undefined) {
    return <div>Group not found</div>;
  } else {
    return (
      <div className={styles.group}>
        { /* <div className={styles.name}>{id}</div> */ }
        <b>Name: </b>{name}
        <ul>
          {
            users.map((user, idx) => (
              <li key={user.id}>
                <Link to={`/users/${user.id}`}>{user.username}</Link>&nbsp;
              {(currentUser.roles.includes('Super admin') ||
                currentUser.roles.includes('Group admin')) &&
               <button type="button">Remove from group</button>
              }
              </li>
            ))
          }
        </ul>
        {currentUser.roles.includes('Super admin') &&
         <NewGroupUserForm group_id={id} />
        }
      </div>
    );
  }
};

Group.propTypes = {
  name: PropTypes.string.isRequired,
  id: PropTypes.number.isRequired,
  users: PropTypes.arrayOf(PropTypes.object).isRequired,
  currentUser: PropTypes.object.isRequired
};


export default Group;
