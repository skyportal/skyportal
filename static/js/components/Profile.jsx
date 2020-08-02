import React from 'react';
import { useSelector } from 'react-redux';

import NewTokenForm from './NewTokenForm';
import TokenList from './TokenList';
import UpdateProfileForm from './UpdateProfileForm';
import ShowUserInfo from './ShowUserInfo';

const Profile = () => {
  const profile = useSelector((state) => state.profile);
  const groups = useSelector((state) => state.groups.user);
  return (
    <div>
      <div>
        <ShowUserInfo />
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
          acls={profile.acls}
          groups={groups}
        />
      </div>
      &nbsp;
      <br />
      <div>
        <TokenList tokens={profile.tokens} />
      </div>
    </div>
  );
};

export default Profile;
