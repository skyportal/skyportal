import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';

import * as candidatesActions from '../ducks/candidates';


const FilterCandidateList = () => {
  const { pageNumber, lastPage, totalMatches, candidateNumberingStart,
    candidateNumberingEnd } = useSelector((state) => state.candidates);

  const [jumpToPageInputValue, setJumpToPageInputValue] = useState("");

  const dispatch = useDispatch();

  const handleClickNextPage = () => {
    dispatch(candidatesActions.fetchCandidates({ pageNumber: pageNumber + 1 }));
  };

  const handleClickPreviousPage = () => {
    dispatch(candidatesActions.fetchCandidates({ pageNumber: pageNumber - 1 }));
  };

  const handleJumpToPageInputChange = (event) => {
    setJumpToPageInputValue(event.target.value);
  };

  const handleClickJumpToPage = (event) => {
    event.preventDefault();
    dispatch(candidatesActions.fetchCandidates(jumpToPageInputValue));
  };

  return (
    <div>
      <div style={{ display: "inline-block" }}>
        <button
          type="button"
          onClick={handleClickPreviousPage}
          disabled={pageNumber === 1}
        >
          Previous Page
        </button>
      </div>
      <div style={{ display: "inline-block" }}>
        <i>
          Displaying&nbsp;
          {candidateNumberingStart}
          -
          {candidateNumberingEnd}
          &nbsp;
          of&nbsp;
          {totalMatches}
          &nbsp;
          candidates.
        </i>
      </div>
      <div style={{ display: "inline-block" }}>
        <button
          type="button"
          onClick={handleClickNextPage}
          disabled={lastPage}
        >
          Next Page
        </button>
      </div>
      <div>
        <i>
          or&nbsp;&nbsp;
        </i>
        <button type="button" onClick={handleClickJumpToPage}>
          Jump to page:
        </button>
        &nbsp;&nbsp;
        <input
          type="text"
          style={{ width: "25px" }}
          onChange={handleJumpToPageInputChange}
          value={jumpToPageInputValue}
          name="jumpToPageInputField"
        />
      </div>
    </div>
  );
};

export default FilterCandidateList;
