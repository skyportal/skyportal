import React from 'react';
import { connect } from "react-redux";

import Source from './Source';


let SourceList = ({sources}) => (
  <div>
    {
      sources.map((source) => (
        <Source {...source}/>
      ))
    }
  </div>
);

const mapStateToProps = (state, ownProps) => {
  return {
    sources: state.sources
  };
};

SourceList = connect(mapStateToProps)(SourceList);

export default SourceList;
