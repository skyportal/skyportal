import React, { useRef } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import Dropdown, { DropdownTrigger, DropdownContent } from 'react-simple-dropdown';
import styled from 'styled-components';

import styles from "./ProfileDropdown.css";
import ShowAvatar from './ShowAvatar';

const Container = styled.div`
  padding: 1em;
  color: white;
  font-weight: normal;
  float: right;
  vertical-align: middle;

  @media only screen and (max-width: 768px) {
    position: absolute;
    right: 15px;
    top: 20px;
    z-index: 200;
  }
`;

const ProfileDropdown = () => {
  const profile = useSelector((state) => state.profile);
  const dropdown = useRef(null);

  const collapseDropdown = () => {
    dropdown.current.hide();
  };

  return (
    <Container>
      <Dropdown ref={dropdown}>
        <DropdownTrigger>
          <div style={{ display: "flex",
            justifyContent: "space-between",
            flexDirection: "row",
            alignItems: "center" }}
          >
            <ShowAvatar
              size={32}
              firstName={profile.first_name}
              lastName={profile.last_name}
              username={profile.username}
              gravatarUrl={profile.gravatar_url}
            />
          &nbsp;&nbsp;
            { profile.username }
            {' '}
          &nbsp;▾
          </div>
        </DropdownTrigger>

        <DropdownContent>
          <Link to="/profile" role="link">
            <div role="menuitem" tabIndex="0" className={styles.entry} onClick={collapseDropdown}>
              Profile
            </div>
          </Link>

          <div className={styles.rule} />

          <Link to="/groups" role="link">
            <div role="menuitem" tabIndex="-1" className={styles.entry} onClick={collapseDropdown}>
              Groups
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
    </Container>
  );
};

export default ProfileDropdown;
