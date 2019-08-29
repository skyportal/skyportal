import React from 'react';
import { useSelector } from 'react-redux';

import GroupManagement from './GroupManagement';
import GroupList from './GroupList';


const Groups = (props) => {
  const roles = useSelector((state) => state.profile.roles);
  return (
    <div>
      {roles.includes("Super admin") && <GroupManagement />}
      <GroupList title="My Groups" />
    </div>
  );
};

export default Groups;
