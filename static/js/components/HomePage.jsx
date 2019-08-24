import React from 'react';
import PropTypes from 'prop-types';

import SourceList from './SourceList';
import GroupList from './GroupList';


const HomePage = ({ groups }) => (
  <div>
    <div style={{ float: "left" }}>
      <SourceList />
    </div>
    <div style={{ float: "left" }}>
      <GroupList title="My Groups" groups={groups} />
    </div>
  </div>
);
HomePage.propTypes = {
  groups: PropTypes.arrayOf(PropTypes.object).isRequired
};


export default HomePage;
