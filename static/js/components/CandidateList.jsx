import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';

import * as sourceActions from '../ducks/source';
import * as candidatesActions from '../ducks/candidates';
import sourceStyles from "./Source.css";
import Plot from './Plot';
import ThumbnailList from './ThumbnailList';


const CandidateList = () => {
  const { candidateList, pageNumber, lastPage, totalMatches,
          sourceNumberingStart, sourceNumberingEnd } = useSelector((state) =>
            state.candidates
          );

  const dispatch = useDispatch();
  const [jumpToPageInputValue, setJumpToPageInputValue] = useState("");

  useEffect(() => {
    if (!candidateList.length) {
      dispatch(candidatesActions.fetchCandidates());
    }
  }, []);

  const handleClickNextPage = (event) => {
    dispatch(candidatesActions.fetchCandidates({ pageNumber: pageNumber + 1 }));
  };

  const handleClickPreviousPage = (event) => {
    dispatch(candidatesActions.fetchCandidates({ pageNumber: pageNumber - 1 }));
  };

  const handleJumpToPageInputChange = (event) => {
    setJumpToPageInputValue(event.target.value);
  };

  const handleClickJumpToPage = (event) => {
    event.preventDefault();
    dispatch(candidatesActions.fetchCandidates({ pageNumber: jumpToPageInputValue }));
  };

  const handleIsCandidateRadioClick = (value, candidate_id) => {
    dispatch(sourceActions.updateSource(candidate_id, { is_candidate: value }));
  };

  return (
    <div style={{ border: "1px solid #DDD", padding: "10px" }}>
      <h2>
        Scan candidates for sources
      </h2>
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
            {sourceNumberingStart}
            -
            {sourceNumberingEnd}
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
      <table>
        <thead>
          <tr>
            <th>
              Last detected
            </th>
            <th>
              Images
            </th>
            <th>
              Info
            </th>
            <th>
              Photometry
            </th>
          </tr>
        </thead>
        <tbody>
          {
            candidateList.map((candidate) => {
              const thumbnails = candidate.thumbnails.filter((t) => t.type != "dr8");
              return (
                <tr key={candidate.id}>
                  <td>
                    {candidate.last_detected && String(candidate.last_detected).split(".")[0]}
                  </td>
                  <td>
                    <ThumbnailList
                      ra={candidate.ra}
                      dec={candidate.dec}
                      thumbnails={thumbnails}
                    />
                  </td>
                  <td>
                    <div style={{ display: "inline-block", float: "right", paddingRight: "50px" }}>
                      <input
                        type="radio"
                        name={`isCandidate${candidate.id}`}
                        id={`isCandidateTrueRadio${candidate.id}`}
                      // eslint-disable-next-line react/jsx-boolean-value
                        value={true}
                        checked={candidate.is_candidate}
                        onClick={() => { handleIsCandidateRadioClick(true, candidate.id) }}
                      />
                &nbsp;Is candidate
                <br />
                <input
                  type="radio"
                  name={`isCandidate${candidate.id}`}
                  id={`isCandidateFalseRadio${candidate.id}`}
                  value={false}
                  checked={!candidate.is_candidate}
                  onClick={() => { handleIsCandidateRadioClick(false, candidate.id) }}
                />
                &nbsp;Is source
                    </div>
                  </td>
                  <td>
                    <Plot
                      className={sourceStyles.smallPlot}
                      url={`/api/internal/plot/photometry/${candidate.id}`}
                    />
                  </td>
                </tr>
              );
            })
          }
        </tbody>
      </table>
    </div>
  );
};

export default CandidateList;
