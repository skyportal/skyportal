import Box from "@mui/material/Box";

import { useGetProfileQuery } from "../../ducks/profile";
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
    </Box>
  );
};

export default Profile;
