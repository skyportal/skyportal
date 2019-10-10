import React, { useRef } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import Dropdown, { DropdownTrigger, DropdownContent } from 'react-simple-dropdown';

import styles from "./ProfileDropdown.css";
import Responsive from "./Responsive";


const ProfileDropdown = (props) => {
  const profile = useSelector((state) => state.profile);
  const dropdown = useRef(null);

  const collapseDropdown = () => {
    dropdown.current.hide();
  };

  return (
    <Responsive
      desktopStyle={styles.profileDesktop}
      mobileStyle={styles.profileMobile}
    >

      <Dropdown ref={dropdown}>

        <DropdownTrigger>
          { profile.username }
          {' '}
          &nbsp;▾
        </DropdownTrigger>

        <DropdownContent>

          <Link to="/profile" role="link">
            <div className={styles.entry} onClick={collapseDropdown}>
              Profile
            </div>
          </Link>

          <div className={styles.rule} />

          <Link to="/groups" role="link">
            <div className={styles.entry} onClick={collapseDropdown}>
              Groups
            </div>
          </Link>

          <div className={styles.rule} />

          <a href="https://github.com/skyportal/skyportal/issues/new">
            <div className={styles.entry} onClick={collapseDropdown}>
              File an issue
            </div>
          </a>

          <a href="https://github.com/skyportal/skyportal">
            <div className={styles.entry} onClick={collapseDropdown}>
              Help
            </div>
          </a>

          <div className={styles.rule} />

          <a href="/logout">
            <div className={styles.entry} onClick={collapseDropdown}>
              Sign out
            </div>
          </a>

        </DropdownContent>

      </Dropdown>

    </Responsive>
  );
};

export default ProfileDropdown;
