import { useState } from "react";
import { Link } from "react-router-dom";

import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import MenuList from "@mui/material/MenuList";
import Popover from "@mui/material/Popover";
import Typography from "@mui/material/Typography";
import LogoutIcon from "@mui/icons-material/Logout";
import PersonIcon from "@mui/icons-material/PersonOutlined";

import { useGetProfileQuery } from "../ducks/profile";
import Button from "./Button";
import UserAvatar from "./user/UserAvatar";

const ProfileDropdown = () => {
  const { data: profile } = useGetProfileQuery();
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);

  // In the header of every page: render nothing, not a spinner, while loading.
  if (!profile) return null;

  const handleClose = () => setAnchorEl(null);

  const avatarProps = {
    firstName: profile.first_name ?? null,
    lastName: profile.last_name ?? null,
    username: profile.username,
    gravatarUrl: profile.gravatar_url!,
    noTooltip: true,
  };

  return (
    <>
      <IconButton
        color="primary"
        aria-label="profile"
        component="span"
        onClick={(event) => setAnchorEl(event.currentTarget)}
        data-testid="avatar"
        size="large"
        sx={{ p: 0, m: 0 }}
      >
        <UserAvatar size={45} {...avatarProps} />
      </IconButton>
      {/* this is to make baselayer.app.test_util.login happy */}
      <Box component="span" sx={{ display: "none" }}>
        {profile.username}
      </Box>
      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{
          paper: {
            sx: {
              mt: 1,
              borderRadius: 2,
              minWidth: "15rem",
              maxWidth: "20rem",
            },
          },
        }}
        disableScrollLock
      >
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 0.5,
            px: 3,
            py: 2.5,
            bgcolor: "action.hover",
          }}
        >
          <UserAvatar size={64} {...avatarProps} />
          {(profile.first_name || profile.last_name) && (
            <Typography
              noWrap
              data-testid="firstLastName"
              sx={{ mt: 1, maxWidth: "100%", fontWeight: 600 }}
            >
              {profile.first_name} {profile.last_name}
            </Typography>
          )}
          <Typography
            noWrap
            variant="body2"
            color="text.secondary"
            data-testid="username"
            sx={{ maxWidth: "100%" }}
          >
            @{profile.username}
          </Typography>
        </Box>
        <Divider />
        {profile.is_anonymous ? (
          <Box sx={{ display: "flex", justifyContent: "center", p: 2 }}>
            <Button href="/" primary>
              Log in
            </Button>
          </Box>
        ) : (
          <MenuList
            sx={{ py: 1, "& .MuiMenuItem-root": { gap: 1.5, py: 1, px: 2.5 } }}
          >
            <MenuItem
              component={Link}
              to="/profile"
              role="link"
              onClick={handleClose}
            >
              <PersonIcon fontSize="small" color="action" />
              Profile
            </MenuItem>
            <MenuItem component="a" href="/logout" data-testid="signOutButton">
              <LogoutIcon fontSize="small" color="action" />
              Sign out
            </MenuItem>
          </MenuList>
        )}
      </Popover>
    </>
  );
};

export default ProfileDropdown;
