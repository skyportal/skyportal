import React from 'react';
import { Link } from 'react-router-dom';
import Source from './Source';

let SourceList = ({sources, ...rest}) => (
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

export default SourceList;
