import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { useSelector } from 'react-redux';

import SourceList from './SourceList';


const GroupList = ({ title, listSources }) => {
  const groups = useSelector(state => state.groups.latest);
  return (
    <div>
      <h2>
        {title}
      </h2>
      <ul>
        {
          groups &&
          groups.map((group, idx) => (
            <li key={group.id}>
              <Link to={`/group/${group.id}`}>
                {group.name}
              </Link>
              {
                listSources &&
                <SourceList sources={group.sources} showTitle={false} />
              }
            </li>
          ))
        }
      </ul>
    </div>
  );
};

GroupList.propTypes = {
  title: PropTypes.string.isRequired,
  listSources: PropTypes.bool
};
GroupList.defaultProps = {
  listSources: false
};


export default GroupList;
