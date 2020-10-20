import React from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";

import MenuItem from "@material-ui/core/MenuItem";
import MenuList from "@material-ui/core/MenuList";

import { makeStyles } from "@material-ui/core/styles";
import Box from "@material-ui/core/Box";
import Popover from "@material-ui/core/Popover";
import Typography from "@material-ui/core/Typography";
import Button from "@material-ui/core/Button";

import IconButton from "@material-ui/core/IconButton";
import Divider from "@material-ui/core/Divider";
import UserAvatar from "./UserAvatar";

const useStyles = makeStyles((theme) => ({
  avatar: {
    padding: `${theme.spacing(2)}px 0 ${theme.spacing(1)}px 0`,
  },
  nodecor: {
    textDecoration: "none",
    textAlign: "center",
    color: theme.palette.text.primary,
  },
  centerContent: {
    justifyContent: "center",
  },
  signOutMargin: {
    margin: `0 0 ${theme.spacing(2)}px 0`,
  },
  typography: {
    padding: theme.spacing(1),
  },
  invisible: {
    display: "none",
  },
  paddingSides: {
    margin: `0 ${theme.spacing(2)}px 0 ${theme.spacing(2)}px`,
  },
  popoverMenu: {
    minWidth: "10rem",
    maxWidth: "20rem",
  },
}));

const ProfileDropdown = () => {
  const profile = useSelector((state) => state.profile);

  const classes = useStyles();
  const [anchorEl, setAnchorEl] = React.useState(null);

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const open = Boolean(anchorEl);
  const id = open ? "simple-popover" : undefined;

  return (
    <div>
      <IconButton
        color="primary"
        aria-label="profile"
        component="span"
        onClick={handleClick}
        data-testid="avatar"
      >
        <UserAvatar
          size={50}
          firstName={profile.first_name}
          lastName={profile.last_name}
          username={profile.username}
          gravatarUrl={profile.gravatar_url}
        />
      </IconButton>

      {/* this is to make baselayer.app.test_util.login happy */}
      <span className={classes.invisible}>{profile.username}</span>

      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
      >
        <Box
          display="flex"
          justifyContent="center"
          className={classes.avatar}
          bgcolor="background.paper"
        >
          <UserAvatar
            size={60}
            firstName={profile.first_name}
            lastName={profile.last_name}
            username={profile.username}
            gravatarUrl={profile.gravatar_url}
          />
        </Box>
        <Box display="flex" justifyContent="center" bgcolor="background.paper">
          {(profile?.first_name?.length > 0 ||
            profile?.last_name?.length > 0) && (
            <Typography
              className={classes.typography}
              data-testid="firstLastName"
            >
              {profile.first_name} {profile.last_name}
            </Typography>
          )}
        </Box>
        <Box
          display="flex"
          justifyContent="center"
          bgcolor="background.paper"
          className={classes.paddingSides}
        >
          <Typography className={classes.typography} data-testid="username">
            {profile.username.substring(0, 15) +
              (profile.username.length > 15 ? "..." : "")}
          </Typography>
        </Box>
        <Divider />

        <MenuList className={classes.popoverMenu}>
          <Link
            to="/profile"
            role="link"
            className={classes.nodecor}
            onClick={handleClose}
          >
            <MenuItem className={classes.centerContent}>Profile</MenuItem>
          </Link>
        </MenuList>

        <Box
          display="flex"
          justifyContent="center"
          bgcolor="background.paper"
          className={classes.signOutMargin}
        >
          <a
            href="/logout"
            className={classes.nodecor}
            data-testid="signOutButton"
          >
            <Button>Sign out</Button>
          </a>
        </Box>
      </Popover>
    </div>
  );
};

export default ProfileDropdown;
