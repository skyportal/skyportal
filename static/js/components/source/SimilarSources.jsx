import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Tooltip from "@mui/material/Tooltip";
import { Link } from "react-router-dom";

import * as summaryActions from "../../ducks/summary";

const SimilarSources = ({ source, min_score = 0.9, k = 3 }) => {
  const dispatch = useDispatch();
  const usePinecone = useSelector((state) => state.config.usePinecone);
  const [simSourceList, setSimSourceList] = useState([]);

  useEffect(() => {
    if (source?.id && usePinecone) {
      let tmpList = [];
      const queryBundle = {
        objID: source.id,
        // get an extra source to account for the source itself
        k: k + 1,
      };
      dispatch(summaryActions.fetchSummaryQuery(queryBundle)).then(
        (response) => {
          if (response.status === "success") {
            if (response.data) {
              tmpList = response.data?.query_results;
              if (tmpList.length > 0) {
                // remove the source itself from the list
                tmpList = tmpList.filter((item) => item.id !== source.id);
                // remove any sources with a score below the threshold
                tmpList = tmpList.filter((item) => item.score >= min_score);
                setSimSourceList(tmpList);
              } else {
                setSimSourceList([]);
              }
            } else {
              setSimSourceList([]);
            }
          }
          // Don't show an error if the query fails, just don't show any similar sources
        },
      );
    }
  }, [dispatch, source, k, min_score, usePinecone]);

  return (
    <>
      {simSourceList?.length < 1 ? null : (
        <div
          style={{
            display: "flex",
            flexFlow: "row wrap",
            alignItems: "center",
          }}
        >
          <Tooltip
            title={`Highest AI summary similarity scores s>${min_score}`}
          >
            <b style={{ textWrap: "nowrap", marginRight: "0.5rem" }}>
              Similar Sources:
            </b>
          </Tooltip>
          <div
            style={{
              display: "flex",
              flexFlow: "row wrap",
              alignItems: "center",
              columnGap: "0.25rem",
            }}
          >
            {simSourceList.map((item) => {
              let theTitle = `s=${item.score?.toFixed(3)}`;
              if (item.metadata?.redshift) {
                theTitle += ` z=${item.metadata?.redshift?.toFixed(3)}`;
              }
              if (item.metadata?.class) {
                theTitle += ` ${item.metadata?.class}`;
              }
              return (
                <div key={item.id}>
                  <Tooltip title={theTitle}>
                    <Link to={`/source/${item.id}`} role="link" key={item.id}>
                      {item.id}
                    </Link>
                  </Tooltip>
                  &nbsp;&nbsp;
                </div>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
};

SimilarSources.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
  min_score: PropTypes.number,
  k: PropTypes.number,
};

SimilarSources.defaultProps = {
  min_score: 0.9,
  k: 3,
};
export default SimilarSources;
