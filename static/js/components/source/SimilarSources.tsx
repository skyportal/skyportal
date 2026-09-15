import { useEffect, useState } from "react";
import Tooltip from "@mui/material/Tooltip";
import { Link } from "react-router-dom";

import { useFetchSummaryQueryMutation } from "../../ducks/summary";
import { useGetConfigQuery } from "../../ducks/config";

interface SimilarSourcesProps {
  source: {
    id?: string;
    [key: string]: any;
  };
  min_score?: number;
  k?: number;
}

const SimilarSources = ({ source, min_score, k = 3 }: SimilarSourcesProps) => {
  const config = useGetConfigQuery().data as any;
  const useSummarySearch = config?.useSummarySearch;
  // Scores only mean something relative to the embedding model in use, so the
  // cut comes from the config that names it. A prop still wins where a caller
  // has a reason to differ.
  const threshold = min_score ?? config?.summarySearchMinScore;
  const [fetchSummaryQuery] = useFetchSummaryQueryMutation();
  const [simSourceList, setSimSourceList] = useState<any[]>([]);

  useEffect(() => {
    if (source?.id && useSummarySearch) {
      const queryBundle = {
        objID: source.id,
        k,
      };
      fetchSummaryQuery(queryBundle)
        .unwrap()
        .then((data: any) => {
          let tmpList: any[] = data?.query_results ?? [];
          if (tmpList.length > 0) {
            // remove any sources with a score below the threshold
            if (threshold != null) {
              tmpList = tmpList.filter((item) => item.score >= threshold);
            }
            setSimSourceList(tmpList);
          } else {
            setSimSourceList([]);
          }
        })
        .catch(() => {
          // Don't show an error if the query fails, just don't show any similar sources
        });
    }
  }, [fetchSummaryQuery, source, k, threshold, useSummarySearch]);

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
            title={
              threshold != null
                ? `Highest AI summary similarity scores s>${threshold}`
                : "Highest AI summary similarity scores"
            }
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
