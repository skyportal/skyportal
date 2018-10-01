import React from 'react';
import PropTypes from 'prop-types';


const TabulatedSourceListNavigation = (props) => (
  <div>
    <button type="button" onClick={() => props.nextPage(props.pageNumber)}>View Next 100 Sources</button>
    &nbsp;&nbsp;
    {
      props.pageNumber > 1 &&
      <button type="button" onClick={() => props.previousPage(props.pageNumber)}>View Previous 100 Sources</button>
    }
  </div>
);

TabulatedSourceListNavigation.propTypes = {
  previousPage: PropTypes.func.isRequired,
  nextPage: PropTypes.func.isRequired,
  pageNumber: PropTypes.number.isRequired
};

export default TabulatedSourceListNavigation;
