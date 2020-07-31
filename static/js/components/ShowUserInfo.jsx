import React from 'react';
import { useSelector } from 'react-redux';

import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import Typography from '@material-ui/core/Typography';
import Box from '@material-ui/core/Box';
import Grid from '@material-ui/core/Grid';

import ShowAvatar from './ShowAvatar';

const ShowUserInfo = () => {
  const profile = useSelector((state) => state.profile);

  return (
    <Card>
      <CardContent>
        <Grid
          container
          direction="row"
          justify="flex-start"
          alignItems="center"
          spacing={1}
        >
          <Grid item xs={1}>
            <ShowAvatar
              size={128}
              firstName={profile.first_name}
              lastName={profile.last_name}
              username={profile.username}
              gravatarUrl={profile.gravatar_url}
            />
          </Grid>
          <Grid item xs={1}>
            <h2>
              {profile.first_name}
              {' '}
              {profile.last_name}
            </h2>
          </Grid>
        </Grid>
          &nbsp;
        <br />
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
      </CardContent>
    </Card>
  );
};

export default ShowUserInfo;
