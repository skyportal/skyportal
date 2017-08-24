import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import Dropdown, { DropdownTrigger, DropdownContent } from 'react-simple-dropdown';

import styles from "./Profile.css";


const Profile = ({ username }) => (
  <div className={styles.profile}>
    <Dropdown>

      <DropdownTrigger>
        { username } &nbsp;▾
      </DropdownTrigger>

      <DropdownContent className={styles.dropdownContent}>

        <Link to="/profile">
          <div className={styles.entry}>
            Profile
          </div>
        </Link>

        <div className={styles.rule} />

        <div className={styles.entry}>
          Groups
        </div>

        <div className={styles.rule} />

        <a href="https://github.com/skyportal/skyportal/issues/new">
          <div className={styles.entry}>
            File an issue
          </div>
        </a>

        <a href="https://github.com/skyportal/skyportal">
          <div className={styles.entry}>
            Help
          </div>
        </a>

      </DropdownContent>
    </Dropdown>
  </div>
);

Profile.propTypes = {
  username: PropTypes.string.isRequired
};

export default Profile;
