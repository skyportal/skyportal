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
  k?: number;
}

const SimilarSources = ({ source, k = 3 }: SimilarSourcesProps) => {
  const config = useGetConfigQuery().data as any;
  const useSummarySearch = config?.useSummarySearch;
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
          setSimSourceList(data?.query_results ?? []);
        })
        .catch(() => {
          // Don't show an error if the query fails, just don't show any similar sources
        });
    }
  }, [fetchSummaryQuery, source, k, useSummarySearch]);

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
          <Tooltip title="Highest AI summary similarity scores">
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
