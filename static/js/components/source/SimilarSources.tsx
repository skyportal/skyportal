import React, { useEffect, useState } from "react";
import Tooltip from "@mui/material/Tooltip";
import { Link } from "react-router-dom";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as summaryActions from "../../ducks/summary";

interface SimilarSourcesProps {
  source: {
    id?: string;
    [key: string]: any;
  };
  min_score?: number;
  k?: number;
}

const SimilarSources = ({
  source,
  min_score = 0.9,
  k = 3,
}: SimilarSourcesProps) => {
  const dispatch = useAppDispatch();
  const usePinecone = useAppSelector(
    (state) => (state.config as any).usePinecone,
  );
  const [simSourceList, setSimSourceList] = useState<any[]>([]);

  useEffect(() => {
    if (source?.id && usePinecone) {
      let tmpList: any[] = [];
      const queryBundle = {
        objID: source.id,
        // get an extra source to account for the source itself
        k: k + 1,
      };
      dispatch(summaryActions.fetchSummaryQuery(queryBundle)).then(
        (response: any) => {
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

export default SimilarSources;
