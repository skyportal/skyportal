import React, { useRef } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import Dropdown, { DropdownTrigger, DropdownContent } from 'react-simple-dropdown';

import styles from "./ProfileDropdown.css";
import Responsive from "./Responsive";


const ProfileDropdown = () => {
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
            <div role="menuitem" tabIndex="0" className={styles.entry} onClick={collapseDropdown}>
              Profile
            </div>
          </Link>

          <div className={styles.rule} />

          <Link to="/candidates" role="link">
            <div className={styles.entry} onClick={collapseDropdown} role="menuitem" tabIndex="-1">
              Scan Candidates
            </div>
          </Link>

          <div className={styles.rule} />

          <Link to="/sources" role="link">
            <div className={styles.entry} onClick={collapseDropdown} role="menuitem" tabIndex="-1">
              Sources
            </div>
          </Link>

          <div className={styles.rule} />

          <Link to="/groups" role="link">
            <div role="menuitem" tabIndex="-1" className={styles.entry} onClick={collapseDropdown}>
              Groups
            </div>
          </Link>

          <div className={styles.rule} />

          <Link to="/skyportal_info" role="link">
            <div role="menuitem" tabIndex="-1" className={styles.entry} onClick={collapseDropdown}>
              About
            </div>
          </Link>

          <div className={styles.rule} />

          <a href="/logout">
            <div role="menuitem" tabIndex="-1" className={styles.entry} onClick={collapseDropdown}>
              Sign out
            </div>
          </a>

        </DropdownContent>

      </Dropdown>

    </Responsive>
  );
};

export default ProfileDropdown;
