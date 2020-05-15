import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import PropTypes from 'prop-types';

import * as candidatesActions from '../ducks/candidates';
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";


const FilterCandidateList = ({ userGroups }) => {
  const { pageNumber, lastPage, totalMatches, numberingStart,
    numberingEnd } = useSelector((state) => state.candidates);

  const [jumpToPageInputValue, setJumpToPageInputValue] = useState("");
  const today = new Date();
  const todayYMD = (`${today.getFullYear()}-` +
                    // eslint-disable-next-line prefer-template
                    `${("0" + (today.getMonth() + 1)).slice(-2)}-` +
                    // eslint-disable-next-line prefer-template
                    `${("0" + today.getDate()).slice(-2)}`);
  let userGroupIDs = userGroups.map((userGroup) => userGroup.id);
  const [filterParams, setFilterParams] = useState({
    unsavedOnly: false,
    startDate: `${todayYMD}T00:00:00`,
    endDate: `${todayYMD}T23:59:59`,
    groupIDs: [...userGroupIDs]
  });
  // This is often initialized before userGroups data has been received, so we update
  useEffect(() => {
    if (filterParams.groupIDs.length === 0) {
      userGroupIDs = userGroups.map((userGroup) => userGroup.id);
      setFilterParams({ ...filterParams, groupIDs: userGroupIDs });
    }
  }, [userGroups]);

  const dispatch = useDispatch();

  const handleClickNextPage = () => {
    dispatch(candidatesActions.fetchCandidates({ pageNumber: pageNumber + 1 }));
  };

  const handleClickPreviousPage = () => {
    dispatch(candidatesActions.fetchCandidates({ pageNumber: pageNumber - 1 }));
  };

  const handleJumpToPageInputChange = (e) => {
    setJumpToPageInputValue(e.target.value);
  };

  const handleClickJumpToPage = () => {
    dispatch(candidatesActions.fetchCandidates({ pageNumber: jumpToPageInputValue }));
  };

  const handleInputChange = (e) => {
    const filterParamsCopy = { ...filterParams };
    filterParamsCopy.groupIDs = [...filterParams.groupIDs];

    if (e.target.name.startsWith("groupIDCheckBox_")) {
      const groupID = parseInt(e.target.name.split("groupIDCheckBox_")[1], 10);
      if (e.target.checked) {
        filterParamsCopy.groupIDs.push(groupID);
      } else if (!e.target.checked) {
        filterParamsCopy.groupIDs.splice(filterParams.groupIDs.indexOf(groupID), 1);
      }
    } else {
      filterParamsCopy[e.target.name] = e.target.type === 'checkbox' ?
        e.target.checked : e.target.value;
    }
    setFilterParams({
      ...filterParamsCopy,
      groupIDs: [...filterParamsCopy.groupIDs]
    });
  };

  const handleClickSubmit = () => {
    dispatch(candidatesActions.fetchCandidates(filterParams));
  };

  return (
    <div>
      <div>
        <label>
          Start Date (UTC):&nbsp;
        </label>
        <input
          type="text"
          name="startDate"
          value={filterParams.startDate}
          onChange={handleInputChange}
          size="10"
        />
        &nbsp;&nbsp;
        <label>
          End Date (UTC):&nbsp;
        </label>
        <input
          type="text"
          name="endDate"
          value={filterParams.endDate}
          onChange={handleInputChange}
          size="10"
        />
      </div>
      <div>
        <label>
          <b>
            Show only unsaved candidates:&nbsp;
          </b>
        </label>
        <input
          type="checkbox"
          name="unsavedOnly"
          checked={filterParams.unsavedOnly}
          onChange={handleInputChange}
        />
      </div>
      <div>
        <Responsive
          element={FoldBox}
          title="Program Selection"
          mobileProps={{ folded: true }}
        >
          {
            userGroups.map((group) => (
              <div key={`groupSelectDiv${group.id}`}>
                <input
                  type="checkbox"
                  name={`groupIDCheckBox_${group.id}`}
                  checked={filterParams.groupIDs.includes(group.id)}
                  onChange={handleInputChange}
                />
                &nbsp;
                {
                  group.name
                }
              </div>
            ))
          }
        </Responsive>
      </div>
      <div>
        <button type="button" onClick={handleClickSubmit}>
          Submit
        </button>
      </div>
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
          {numberingStart}
          -
          {numberingEnd}
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
FilterCandidateList.propTypes = {
  userGroups: PropTypes.arrayOf(PropTypes.object).isRequired
};

export default FilterCandidateList;
