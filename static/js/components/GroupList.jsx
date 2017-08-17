import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';

const GroupList = ({ groups }) => (
  <div>
    <h2>List of Groups</h2>
    <ul>
      {
        groups.map((group, idx) => (
          <li key={group.id}>
            <Link to={`/group/${group.id}`}>{group.name}</Link>
          </li>
        ))
      }
    </ul>
  </div>
);

GroupList.propTypes = {
  groups: PropTypes.arrayOf(PropTypes.object).isRequired
};


export default GroupList;
