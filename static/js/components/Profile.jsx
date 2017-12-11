import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import Dropdown, { DropdownTrigger, DropdownContent } from 'react-simple-dropdown';

import styles from "./Profile.css";
import Responsive from "./Responsive";


const Profile = props => (
  <Responsive
    desktopStyle={styles.profileDesktop}
    mobileStyle={styles.profileMobile}
  >

    <Dropdown>

      <DropdownTrigger>
        { props.profile.username } &nbsp;▾
      </DropdownTrigger>

      <DropdownContent>

        <Link to="/profile">
          <div className={styles.entry}>
            Profile
          </div>
        </Link>

        <div className={styles.rule} />

        {props.profile.roles.includes("Super admin") &&
        <Link to="/group_management">
          <div className={styles.entry}>
            <font color="red">Super Admin: </font>Manage Groups &nbsp;&nbsp;
          </div>
        </Link>
        }

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

        <div className={styles.rule} />

        <a href="/logout">
          <div className={styles.entry}>
            Sign out
          </div>
        </a>

      </DropdownContent>

    </Dropdown>

  </Responsive>
);

Profile.propTypes = {
  profile: PropTypes.object.isRequired
};

export default Profile;
