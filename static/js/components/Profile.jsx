import React from 'react';
import PropTypes from 'prop-types';


const Profile = props => (
  <div>
    <div>
Username:
      {props.profile.username}
    </div>
    <br />
    <div>
User roles:
      {props.profile.roles}
    </div>
  </div>
);
Profile.propTypes = {
  profile: PropTypes.object.isRequired
};

export default Profile;
