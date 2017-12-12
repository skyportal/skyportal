import React from 'react';

import GroupManagement from '../containers/GroupManagement';


const Profile = props => (
  <div>
    <div>Username: {props.profile.username}</div>
    <br />
    <div>User roles: {props.profile.roles}</div>
    <br />
    <GroupManagement />
  </div>
);

export default Profile;
