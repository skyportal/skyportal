import React from 'react';
import PropTypes from 'prop-types';
import styles from "./Profile.css";


const Profile = ({ username }) => (
  <div className={styles.profile}>
    { username } &nbsp;▾
  </div>
);

Profile.propTypes = {
  username: PropTypes.string.isRequired
};

export default Profile;
