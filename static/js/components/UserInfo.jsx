import React from 'react';
import PropTypes from 'prop-types';

const UserInfo = ({ username, created_at, acls }) => (
  <div>
    <b>{username}</b>
    <ul>
      <li><b>created_at:</b> {created_at}</li>
      <li><b>acls:</b> {acls.join(', ')}</li>
    </ul>
  </div>
);
UserInfo.propTypes = {
  username: PropTypes.string.isRequired,
  created_at: PropTypes.string,
  acls: PropTypes.arrayOf(PropTypes.string)
};
UserInfo.defaultProps = {
  created_at: '',
  acls: []
};

export default UserInfo;
