import React from 'react';
import { useSelector } from 'react-redux';

import SourceList from './SourceList';
import GroupList from './GroupList';


const HomePage = (props) => {
  const groups = useSelector((state) => state.groups.latest);
  return (
    <div>
      <div style={{ float: "left" }}>
        <SourceList />
      </div>
      <div style={{ float: "left" }}>
        <GroupList title="My Groups" groups={groups} />
      </div>
    </div>
  );
};

export default HomePage;
