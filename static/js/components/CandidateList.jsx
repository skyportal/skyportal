import React, { useEffect, Suspense } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { Link } from 'react-router-dom';

import * as candidatesActions from '../ducks/candidates';
import ThumbnailList from './ThumbnailList';
import CandidateCommentList from './CandidateCommentList';
import SaveCandidateButton from './SaveCandidateButton';
import FilterCandidateList from './FilterCandidateList';

const VegaPlot = React.lazy(() => import(/* webpackChunkName: "VegaPlot" */ './VegaPlot'));


const CandidateList = () => {
  const { candidates } = useSelector((state) => state.candidates);

  const userGroups = useSelector((state) => state.groups.user);

  const dispatch = useDispatch();

  useEffect(() => {
    if (candidates === null) {
      dispatch(candidatesActions.fetchCandidates());
    }
  }, [candidates, dispatch]);

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
            !!candidates && candidates.map((candidateObj) => {
              const thumbnails = candidateObj.thumbnails.filter((t) => t.type !== "dr8");
              return (
                <tr key={candidateObj.id}>
                  <td>
                    {
                      candidateObj.last_detected && (
                        <div>
                          <div>
                            {String(candidateObj.last_detected).split(".")[0].split("T")[1]}
                          </div>
                          <div>
                            {String(candidateObj.last_detected).split(".")[0].split("T")[0]}
                          </div>
                        </div>
                      )
                    }
                  </td>
                  <td>
                    <ThumbnailList
                      ra={candidateObj.ra}
                      dec={candidateObj.dec}
                      thumbnails={thumbnails}
                    />
                  </td>
                  <td>
                    ID:&nbsp;
                    <Link to={`/candidate/${candidateObj.id}`}>
                      {candidateObj.id}
                    </Link>
                    <br />
                    {
                      candidateObj.is_source ? (
                        <div>
                          <Link
                            to={`/source/${candidateObj.id}`}
                            style={{ color: "red", textDecoration: "underline" }}
                          >
                            Previously Saved
                          </Link>
                        </div>
                      ) : (
                        <div>
                          NOT SAVED
                          <br />
                          <SaveCandidateButton
                            candidate={candidateObj}
                            userGroups={userGroups}
                          />
                        </div>
                      )
                    }
                    <b>Coordinates</b>
                    :&nbsp;
                    {candidateObj.ra}
                    &nbsp;
                    {candidateObj.dec}
                    <br />
                  </td>
                  <td>
                    <Suspense fallback={<div>Loading plot...</div>}>
                      <VegaPlot
                        dataUrl={`/api/sources/${candidateObj.id}/photometry`}
                      />
                    </Suspense>
                  </td>
                  <td>
                    {
                      candidateObj.comments &&
                        <CandidateCommentList comments={candidateObj.comments} />
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
