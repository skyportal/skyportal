import Box from "@mui/material/Box";

import { useGetProfileQuery } from "../../ducks/profile";
import JoinableStreamsList from "./JoinableStreamsList";
import NewTokenForm from "./NewTokenForm";
import TokenList from "./TokenList";
import UserPreferences from "./preferences/UserPreferences";
import UserProfileInfo from "./UserProfileInfo";

const Profile = () => {
  const { data: profile } = useGetProfileQuery();

  if (profile?.is_anonymous) {
    return (
      <>
        Please <a href="/">log in</a> to view your profile.
      </>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <UserProfileInfo />
      <UserPreferences />
      <JoinableStreamsList />
      <NewTokenForm availableAcls={profile?.permissions} />
      <TokenList tokens={(profile as any)?.tokens} />
    </Box>
  );
};

export default Profile;
