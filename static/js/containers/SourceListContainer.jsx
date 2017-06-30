import React from 'react';
import { connect } from 'react-redux';

import SourceList from '../components/SourceList';

const mapStateToProps = (state, ownProps) => {
  return {
    sources: state.sources.latest
  };
};

export default connect(mapStateToProps)(SourceList);
