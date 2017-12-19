import React from 'react';

import NewGroupForm from '../containers/NewGroupForm';
import SuperAdminGroupList from '../containers/SuperAdminGroupList';


const GroupManagement = props => (
  <div>
    <NewGroupForm />
    <SuperAdminGroupList title="All Groups" />
  </div>
);

export default GroupManagement;
