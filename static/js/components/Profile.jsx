import React from 'react';
import styles from "./Profile.css";


const Profile = ({ username }) => (
  <div className={styles.profile}>
    { username }
  </div>
);

export default Profile;
