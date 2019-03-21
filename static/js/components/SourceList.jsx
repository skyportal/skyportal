import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';


const SourceList = ({ sources }) => {
  if (typeof sources === 'string' || sources instanceof String) {
    return (
      <div>
        <h2>
          Sources
        </h2>
        <div>
          {sources}
        </div>
      </div>
    );
  } else {
    return (
      <div>
        <h2>
          Sources
        </h2>
        <ul>
          {
            sources.map((source, idx) => (
              <li key={source.id}>
                <Link to={`/source/${source.id}`}>
                  {source.id}
                </Link>
              </li>
            ))
          }
        </ul>
      </div>
    );
  }
};

SourceList.propTypes = {
  sources: PropTypes.arrayOf(PropTypes.object).isRequired
};


export default SourceList;
