import React from 'react';
import { connect } from 'react-redux';

import GroupList from '../components/GroupList';

const mapStateToProps = (state, ownProps) => {
  return {
    groups: state.groups.latest
  };
};

export default connect(mapStateToProps)(GroupList);
