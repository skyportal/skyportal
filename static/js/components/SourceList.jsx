import React from 'react';
import { connect } from 'react-redux';
import { Link } from 'react-router-dom';

import Source from './Source';


let SourceList = ({sources}) => (
  <div>
    <h2>List of Sources</h2>
    <ul>
      {
        sources.map((source, idx) => (
          <li key={idx}>
            <Link to={`/source/${source.id}`}>{source.id}</Link>
          </li>
        ))
      }
    </ul>
  </div>
);

const mapStateToProps = (state, ownProps) => {
  return {
    sources: state.sources.latest
  };
};

SourceList = connect(mapStateToProps)(SourceList);

export default SourceList;
