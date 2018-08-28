import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';

const GroupList = ({ groups, title }) => (
  <div>
    <h2>
      {title}
    </h2>
    <ul>
      {
        groups
        && groups.map((group, idx) => (
          <li key={group.id}>
            <Link to={`/group/${group.id}`}>
              {group.name}
            </Link>
          </li>
        ))
      }
    </ul>
  </div>
);

GroupList.propTypes = {
  groups: PropTypes.arrayOf(PropTypes.object).isRequired,
  title: PropTypes.string.isRequired
};


export default GroupList;
