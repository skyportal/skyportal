import React from 'react';
import PropTypes from 'prop-types';

import SourceListContainer from '../containers/SourceListContainer';
import GroupList from '../containers/GroupListContainer';


const HomePage = (props) => (
  <div>
    <div style={{ float: "left" }}>
      <SourceListContainer />
    </div>
    <div style={{ float: "left" }}>
      <GroupList title="My Groups" groups={props.groups} />
    </div>
  </div>
);
HomePage.propTypes = {
  groups: PropTypes.arrayOf(PropTypes.object).isRequired
};


export default HomePage;
