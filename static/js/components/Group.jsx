import React from 'react'

import styles from "./Group.css";


const Group = ({ name, id }) => {
  if (id === undefined) {
    return <div>Group not found</div>;
  } else {
    return (
      <div className={styles.group}>
        {/*<div className={styles.name}>{id}</div>*/}
        <b>Name: </b>{name}

    </div>
    );
  }
};


export default Group;
