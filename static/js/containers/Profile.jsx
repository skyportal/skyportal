import React from 'react';
import { connect } from 'react-redux';

import Profile from '../components/Profile';

const mapStateToProps = (state, ownProps) => {
  return state.profile;
};

export default connect(mapStateToProps)(Profile);
