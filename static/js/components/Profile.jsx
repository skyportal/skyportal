import React from 'react';
import PropTypes from 'prop-types';

import NewTokenForm from '../containers/NewTokenForm';
import TokenList from './TokenList';


const Profile = props => (
  <div>
    <div>Username: {props.profile.username}</div>
    <br />
    <div>User roles: {props.profile.roles}</div>
    <br />
    <NewTokenForm
      profile={props.profile}
      groups={props.groups}
    />
    <br />
    <TokenList tokens={props.profile.tokens} />
  </div>
);
Profile.propTypes = {
  profile: PropTypes.object.isRequired,
  groups: PropTypes.object
};

export default Profile;
