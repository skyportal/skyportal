import React, { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { Link } from 'react-router-dom';

import * as candidatesActions from '../ducks/candidates';
import sourceStyles from "./Source.css";
import Plot from './Plot';
import ThumbnailList from './ThumbnailList';
import CandidateCommentList from './CandidateCommentList';
import SaveCandidateGroupSelectDialog from './SaveCandidateGroupSelectDialog';
import FilterCandidateList from './FilterCandidateList';


const CandidateList = () => {
  const { candidates } = useSelector((state) => state.candidates);

  const userGroups = useSelector((state) => state.groups.user);

  const dispatch = useDispatch();

  useEffect(() => {
    if (!candidates.length) {
      dispatch(candidatesActions.fetchCandidates());
    }
  }, []);

  return (
    <div style={{ border: "1px solid #DDD", padding: "10px" }}>
      <h2>
        Scan candidates for sources
      </h2>
      <FilterCandidateList userGroups={userGroups} />
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
            <th>
              Autoannotations
            </th>
          </tr>
        </thead>
        <tbody>
          {
            candidates.map((candidate) => {
              const thumbnails = candidate.thumbnails.filter((t) => t.type !== "dr8");
              return (
                <tr key={candidate.id}>
                  <td>
                    {
                      candidate.last_detected && (
                        <div>
                          <div>
                            {String(candidate.last_detected).split(".")[0].split("T")[1]}
                          </div>
                          <div>
                            {String(candidate.last_detected).split(".")[0].split("T")[0]}
                          </div>
                        </div>
                      )
                    }
                  </td>
                  <td>
                    <ThumbnailList
                      ra={candidate.ra}
                      dec={candidate.dec}
                      thumbnails={thumbnails}
                    />
                  </td>
                  <td>
                    ID:&nbsp;
                    <Link to={`/candidate/${candidate.id}`}>
                      {candidate.id}
                    </Link>
                    <br />
                    {
                      candidate.is_source ? (
                        <div>
                          <Link
                            to={`/source/${candidate.id}`}
                            style={{ color: "red", textDecoration: "underline" }}
                          >
                            Previously Saved
                          </Link>
                        </div>
                      ) : (
                        <div>
                          NOT SAVED
                          <br />
                          <SaveCandidateGroupSelectDialog
                            candidateID={candidate.id}
                            candidateGroups={candidate.candidate_groups}
                            userGroups={userGroups}
                          />
                        </div>
                      )
                    }
                    <b>Coordinates</b>
                    :&nbsp;
                    {candidate.ra}
                    &nbsp;
                    {candidate.dec}
                    <br />
                  </td>
                  <td>
                    <Plot
                      className={sourceStyles.smallPlot}
                      url={`/api/internal/plot/photometry/${candidate.id}?plotHeight=200&plotWidth=300`}
                    />
                  </td>
                  <td>
                    {
                      candidate.candidate_comments &&
                        <CandidateCommentList comments={candidate.candidate_comments} />
                    }
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
