import React from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";

import MenuItem from "@mui/material/MenuItem";
import MenuList from "@mui/material/MenuList";

import makeStyles from "@mui/styles/makeStyles";
import Box from "@mui/material/Box";
import Popover from "@mui/material/Popover";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import UserAvatar from "./user/UserAvatar";

const useStyles = makeStyles((theme) => ({
  center: {
    justifyContent: "center",
  },
  invisible: {
    display: "none",
  },
}));

const ProfileDropdown = () => {
  const classes = useStyles();
  const profile = useSelector((state) => state.profile);
  const [anchorEl, setAnchorEl] = React.useState(null);

  return (
    <>
      <IconButton
        aria-label="profile"
        component="span"
        onClick={(e) => setAnchorEl(e.currentTarget)}
        data-testid="avatar"
        size="large"
        sx={{ padding: 0, margin: 0 }}
      >
        <UserAvatar
          size={45}
          firstName={profile.first_name}
          lastName={profile.last_name}
          username={profile.username}
          gravatarUrl={profile.gravatar_url}
        />
      </IconButton>
      {/* this is to make baselayer.app.test_util.login happy */}
      <span className={classes.invisible}>{profile.username}</span>
      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        disableScrollLock
      >
        <Box display="flex" justifyContent="center" sx={{ padding: "1rem" }}>
          <UserAvatar
            size={60}
            firstName={profile.first_name}
            lastName={profile.last_name}
            username={profile.username}
            gravatarUrl={profile.gravatar_url}
          />
        </Box>
        <MenuList>
          <MenuItem
            component={Link}
            to="/profile"
            onClick={() => setAnchorEl(null)}
            sx={{ flexDirection: "column" }}
          >
            {(profile?.first_name?.length || profile?.last_name?.length) && (
              <Typography data-testid="firstLastName" variant="body1">
                {profile.first_name} {profile.last_name}
              </Typography>
            )}
            <Typography
              data-testid="username"
              variant="body2"
              color="textSecondary"
            >
              {profile.username.substring(0, 22) +
                (profile.username.length > 22 ? "..." : "")}
            </Typography>
          </MenuItem>
          <MenuItem
            component={Link}
            to="/profile"
            onClick={() => setAnchorEl(null)}
            className={classes.center}
          >
            Profile
          </MenuItem>
          <MenuItem
            onClick={() => (window.location.href = "/logout")}
            className={classes.center}
            data-testid="signOutButton"
          >
            Sign Out
          </MenuItem>
        </MenuList>
      </Popover>
    </>
  );
};

export default ProfileDropdown;
