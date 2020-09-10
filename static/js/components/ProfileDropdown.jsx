import React from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import styled from "styled-components";
// import { makeStyles } from "@material-ui/core/styles";

import IconButton from "@material-ui/core/IconButton";
import Menu from "@material-ui/core/Menu";
import MenuItem from "@material-ui/core/MenuItem";
import MoreVertIcon from "@material-ui/icons/MoreVert";

import styles from "./ProfileDropdown.css";
import UserAvatar from "./UserAvatar";

const Container = styled.div`
  padding: 0.1rem;
  color: white;
  font-weight: normal;
  float: right;
  vertical-align: middle;

  @media only screen and (max-width: 768px) {
    position: absolute;
    right: 1rem;
    top: 0.75rem;
    z-index: 200;
  }
`;

const ProfileDropdown = () => {
  const profile = useSelector((state) => state.profile);

  const [anchorEl, setAnchorEl] = React.useState(null);
  const open = Boolean(anchorEl);

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <Container>
      <div className={styles.dropdownTriggerDiv}>
        <UserAvatar
          size={32}
          firstName={profile.first_name}
          lastName={profile.last_name}
          username={profile.username}
          gravatarUrl={profile.gravatar_url}
        />
        <div className={styles.username}>
          &nbsp;&nbsp;
          {profile.username}
          &nbsp;&nbsp;
        </div>
        <IconButton
          aria-label="more"
          aria-controls="long-menu"
          aria-haspopup="true"
          onClick={handleClick}
        >
          <MoreVertIcon className={styles.whitish} />
        </IconButton>
        <Menu
          id="long-menu"
          anchorEl={anchorEl}
          keepMounted
          open={open}
          onClose={handleClose}
        >
          <Link to="/profile" role="link" className={styles.nodecor}>
            <MenuItem key="profile" onClick={handleClose}>
              Profile
            </MenuItem>
          </Link>
          <a href="/logout" className={styles.nodecor}>
            <MenuItem key="profile" onClick={handleClose}>
              Sign out
            </MenuItem>
          </a>
        </Menu>
      </div>
    </Container>
  );
};

export default ProfileDropdown;
