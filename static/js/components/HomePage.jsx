import React from 'react';
import { useSelector } from 'react-redux';

import SourceList from './SourceList';
import GroupList from './GroupList';
import NewsFeed from './NewsFeed';


const HomePage = () => {
  const groups = useSelector((state) => state.groups.latest);
  return (
    <div>
      <div style={{ float: "left", paddingRight: "50px" }}>
        <SourceList />
      </div>
      <div style={{ float: "left", paddingRight: "50px" }}>
        <GroupList title="My Groups" groups={groups} />
      </div>
      <div style={{ float: "left" }}>
        <NewsFeed />
      </div>
    </div>
  );
};

export default HomePage;
