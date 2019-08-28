import React from 'react';
import { useSelector } from 'react-redux';

import NewTokenForm from './NewTokenForm';
import TokenList from './TokenList';


const Profile = (props) => {
  const profile = useSelector((state) => state.profile);
  const groups = useSelector((state) => state.groups.latest);
  return (
    <div>
      <div>
Username:
        {profile.username}
      </div>
      <br />
      <div>
User roles:
        {profile.roles}
      </div>
      <br />
      <NewTokenForm
        profile={profile}
        groups={groups}
      />
      <br />
      <TokenList tokens={profile.tokens} />
    </div>
  );
};

export default Profile;
