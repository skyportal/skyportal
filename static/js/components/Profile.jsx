import React from 'react';
import PropTypes from 'prop-types';

import GroupManagement from '../containers/GroupManagement';


const Profile = props => (
  <div>
    <div>Username: {props.profile.username}</div>
    <br />
    <div>User roles: {props.profile.roles}</div>
    <br />
    {props.profile.roles.includes("Super admin") && <GroupManagement />}
  </div>
);
Profile.propTypes = {
  profile: PropTypes.object.isRequired
};

export default Profile;
