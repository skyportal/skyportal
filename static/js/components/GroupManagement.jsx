import React from 'react';

import NewGroupForm from './NewGroupForm';
import SuperAdminGroupList from './SuperAdminGroupList';


const GroupManagement = () => (
  <div>
    <NewGroupForm />
    <SuperAdminGroupList title="All Groups" />
  </div>
);

export default GroupManagement;
