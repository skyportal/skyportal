import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';

import styles from "./Group.css";


const Group = ({ name, id, users }) => {
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
                <Link to={`/users/${user.id}`}>{user.username}</Link>
              </li>
            ))
          }
        </ul>
      </div>
    );
  }
};

Group.propTypes = {
  name: PropTypes.string.isRequired,
  id: PropTypes.string.isRequired,
  users: PropTypes.arrayOf(PropTypes.object).isRequired
};


export default Group;
