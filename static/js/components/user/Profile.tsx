import { useGetProfileQuery } from "../../ducks/profile";
import JoinableStreamsList from "./JoinableStreamsList";
import NewTokenForm from "./NewTokenForm";
import TokenList from "./TokenList";
import UpdateProfileForm from "./UpdateProfileForm";
import UserPreferences from "./preferences/UserPreferences";
import UserProfileInfo from "./UserProfileInfo";

const Profile = () => {
  const { data: profile } = useGetProfileQuery();
  if (profile?.is_anonymous) {
    return (
      <>
        Please <a href="/login/google-oauth2">log in</a> to view your profile.
      </>
    );
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <UserProfileInfo />
      <UpdateProfileForm />
      <UserPreferences />
      <JoinableStreamsList />
      <NewTokenForm availableAcls={profile?.permissions} />
      <TokenList tokens={(profile as any)?.tokens} />
    </div>
  );
};

export default Profile;
