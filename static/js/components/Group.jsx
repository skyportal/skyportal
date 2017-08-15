import React from 'react'
import { Link } from 'react-router-dom';

import styles from "./Group.css";


const Group = ({ name, id, users=[] }) => {
  if (id === undefined) {
    return <div>Group not found</div>;
  } else {
    return (
      <div className={styles.group}>
        {/*<div className={styles.name}>{id}</div>*/}
        <b>Name: </b>{name}
        <ul>
          {
            users.map((user, idx) => (
              <li key={idx}>
                <Link to={`/users/${user.id}`}>{user.username}</Link>
              </li>
            ))
          }
        </ul>
    </div>
    );
  }
};


export default Group;
