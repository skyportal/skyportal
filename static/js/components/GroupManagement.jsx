import React from 'react';
import { useSelector } from 'react-redux';

import Paper from '@material-ui/core/Paper';
import Box from '@material-ui/core/Box';
import Typography from '@material-ui/core/Typography';

import NewGroupForm from './NewGroupForm';
import GroupList from './GroupList';

const GroupManagement = () => {
  const allGroups = useSelector((state) => state.groups.all);

  return (
    <Paper variant="outlined">
      <Box p={1}>
        <Typography variant="h5">
          Group Management
        </Typography>
        <NewGroupForm />
        <GroupList title="All Groups" groups={allGroups} />
      </Box>
    </Paper>
  );
};

export default GroupManagement;
