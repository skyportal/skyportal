import React from 'react';
import { useSelector } from 'react-redux';

import SourceList from './SourceList';
import GroupList from './GroupList';
import NewsFeed from './NewsFeed';


const HomePage = () => {
  const groups = useSelector((state) => state.groups.user);
  return (
    <div>
      <div style={{ float: "left", paddingRight: "40px" }}>
        <SourceList />
      </div>
      <div style={{ float: "left", paddingRight: "40px", paddingBottom: "40px" }}>
        <NewsFeed />
      </div>
      <div style={{ float: "left", paddingRight: "40px" }}>
        <GroupList title="My Groups" groups={groups} />
      </div>
    </div>
  );
};

export default HomePage;
