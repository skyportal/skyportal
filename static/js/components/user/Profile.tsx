import { useState } from "react";

import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";

import { useGetProfileQuery } from "../../ducks/profile";
import JoinableStreamsList from "./JoinableStreamsList";
import NewTokenForm from "./NewTokenForm";
import PublicProfile from "./PublicProfile";
import TokenList from "./TokenList";
import UpdateProfileForm from "./UpdateProfileForm";
import UserPreferences from "./preferences/UserPreferences";
import UserProfileInfo from "./UserProfileInfo";

const Profile = () => {
  const { data: profile } = useGetProfileQuery();
  const [view, setView] = useState("settings");

  if (profile?.is_anonymous) {
    return (
      <>
        Please <a href="/">log in</a> to view your profile.
      </>
    );
  }
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <ToggleButtonGroup
        size="small"
        exclusive
        value={view}
        onChange={(_e, v) => v && setView(v)}
        sx={{ alignSelf: "flex-start" }}
      >
        <ToggleButton value="settings" data-testid="profile-settings-view">
          Settings
        </ToggleButton>
        <ToggleButton value="public" data-testid="profile-public-view">
          Public profile
        </ToggleButton>
      </ToggleButtonGroup>
      {view === "public" ? (
        <>
          <Typography variant="body2" color="textSecondary">
            This is what other users see. Pick what to share from Preferences
            &gt; Public profile.
          </Typography>
          <PublicProfile userId={profile?.id} />
        </>
      ) : (
        <>
          <UserProfileInfo />
          <UpdateProfileForm />
          <UserPreferences />
          <JoinableStreamsList />
          <NewTokenForm availableAcls={profile?.permissions} />
          <TokenList tokens={(profile as any)?.tokens} />
        </>
      )}
    </Box>
  );
};

export default Profile;
