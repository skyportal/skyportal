import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import NewTokenForm from "./NewTokenForm";
import TokenList from "./TokenList";
import UpdateProfileForm from "./UpdateProfileForm";
import UserProfileInfo from "./UserProfileInfo";

const Profile = () => {
  const { data: profile } = useGetProfileQuery();
  const { data: groupsData } = useGetGroupsQuery();
  const groups = groupsData?.user ?? [];
  if (profile?.is_anonymous) {
    return (
      <div>
        Please <a href="/login/google-oauth2">log in</a> to view your profile.
      </div>
    );
  }
  return (
    <div>
      <div>
        <UserProfileInfo />
      </div>
      &nbsp;
      <br />
      <div>
        <UpdateProfileForm />
      </div>
      &nbsp;
      <br />
      <div>
        <NewTokenForm
          availableAcls={profile?.permissions}
          {...({ groups } as any)}
        />
      </div>
      &nbsp;
      <br />
      <div>
        <TokenList tokens={(profile as any)?.tokens} />
      </div>
    </div>
  );
};

export default Profile;
