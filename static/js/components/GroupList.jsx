import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';

import SourceList from './SourceList';


const GroupList = ({ groups, title, listSources }) => (
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
            {
              listSources
              && <SourceList sources={group.sources} showTitle={false} />
            }
          </li>
        ))
      }
    </ul>
  </div>
);

GroupList.propTypes = {
  groups: PropTypes.arrayOf(PropTypes.object).isRequired,
  title: PropTypes.string.isRequired,
  listSources: PropTypes.bool
};
GroupList.defaultProps = {
  listSources: false
};


export default GroupList;
