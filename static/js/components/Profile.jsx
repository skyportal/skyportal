import React from 'react';
import { useSelector } from 'react-redux';
import Typography from '@material-ui/core/Typography';
import Box from '@material-ui/core/Box';

import NewTokenForm from './NewTokenForm';
import TokenList from './TokenList';
import UpdateProfileForm from './UpdateProfileForm';

const Profile = () => {
  const profile = useSelector((state) => state.profile);
  const groups = useSelector((state) => state.groups.user);
  return (
    <div>
      <Typography component="div">
        <Box fontWeight="fontWeightBold" component="span" mr={1}>
          Username:
        </Box>
        {profile.username}
      </Typography>

      <Typography component="div">
        <Box pb={1}>
          <Box fontWeight="fontWeightBold" component="span" mr={1}>
            User roles:
          </Box>
          {profile.roles}
        </Box>
      </Typography>

      <UpdateProfileForm
        profile={profile}
      />

      <NewTokenForm
        acls={profile.acls}
        groups={groups}
      />

      <TokenList tokens={profile.tokens} />

    </div>
  );
};

export default Profile;
