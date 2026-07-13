import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import JoinableStreamsList from "./JoinableStreamsList";
import NewTokenForm from "./NewTokenForm";
import TokenList from "./TokenList";
import UpdateProfileForm from "./UpdateProfileForm";
import UserProfileInfo from "./UserProfileInfo";

const Profile = () => {
  const { data: profile } = useGetProfileQuery();
  const { data: groupsData } = useGetGroupsQuery();
  const groups = groupsData?.user ?? [];
  return (
    <div>
      <div data-testid="tour-profile-info">
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
        <JoinableStreamsList />
      </div>
      &nbsp;
      <br />
      <div data-testid="tour-profile-token">
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
