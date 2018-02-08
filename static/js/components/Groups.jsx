import React from 'react';
import PropTypes from 'prop-types';

import GroupManagement from '../containers/GroupManagement';
import GroupList from '../containers/GroupListContainer';


const Groups = props => (
  <div>
    {props.profile.roles.includes("Super admin") && <GroupManagement />}
    <GroupList title="My Groups" />
  </div>
);
Groups.propTypes = {
  profile: PropTypes.object.isRequired
};

export default Groups;
