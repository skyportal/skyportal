import React from 'react';
import { Link } from 'react-router-dom';
import Group from './Group';

let GroupList = ({groups}) => (
  <div>
    <h2>List of Groups</h2>
    <ul>
      {
        groups.map((group, idx) => (
          <li key={idx}>
            <Link to={`/group/${group.id}`}>{group.name}</Link>
          </li>
        ))
      }
    </ul>
  </div>
);

export default GroupList;
