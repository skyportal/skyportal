import React from 'react';
import { useSelector } from 'react-redux';

import NewTokenForm from './NewTokenForm';
import TokenList from './TokenList';
import UIPreferences from './UIPreferences';


const Profile = () => {
  const profile = useSelector((state) => state.profile);
  const groups = useSelector((state) => state.groups.user);
  return (
    <div>
      <div>
        Username:
        {profile.username}
      </div>

      <div>
        User roles:
        {profile.roles}
      </div>

      <NewTokenForm
        acls={profile.acls}
        groups={groups}
      />

      <TokenList tokens={profile.tokens} />

      <UIPreferences />
    </div>
  );
};

export default Profile;
