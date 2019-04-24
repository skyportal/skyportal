import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import HomePage from '../components/HomePage';


const HomePageContainer = ({ groups }) => (
  <HomePage groups={groups} />
);
HomePageContainer.propTypes = {
  groups: PropTypes.arrayOf(PropTypes.object)
};

HomePageContainer.defaultProps = {
  groups: null
};

const mapStateToProps = (state, ownProps) => (
  {
    groups: state.groups.latest
  }
);

export default connect(mapStateToProps)(HomePageContainer);
