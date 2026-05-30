import React from "react";

import { useAppSelector } from "../../types/hooks";
import NewTokenForm from "./NewTokenForm";
import TokenList from "./TokenList";
import UpdateProfileForm from "./UpdateProfileForm";
import UserProfileInfo from "./UserProfileInfo";

const Profile = () => {
  const profile = useAppSelector((state) => state.profile);
  const groups = useAppSelector((state) => state.groups.user);
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
          availableAcls={profile.permissions}
          {...({ groups } as any)}
        />
      </div>
      &nbsp;
      <br />
      <div>
        <TokenList tokens={(profile as any).tokens} />
      </div>
    </div>
  );
};

export default Profile;
