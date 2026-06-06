import { useState } from "react";

import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";

import { showNotification } from "baselayer/components/Notifications";
import UninitializedDBMessage from "../UninitializedDBMessage";
import SourceTable from "./SourceTable";
import Spinner from "../Spinner";
import ProgressIndicator from "../ProgressIndicators";
import { useAppDispatch } from "../../types/hooks";
import {
  useFetchSourcesQuery,
  useLazyFetchSourcesQuery,
} from "../../ducks/sources";
import { useGetDbInfoQuery } from "../../ducks/dbInfo";

const SourceList = () => {
  const dispatch = useAppDispatch();

  const [queryParams, setQueryParams] = useState<any>({});
  const { data: sourcesState } = useFetchSourcesQuery(queryParams);
  const [fetchSourcesTrigger] = useLazyFetchSourcesQuery();
  const sourceTableEmpty = (useGetDbInfoQuery().data as any)
    ?.source_table_empty;

  const [rowsPerPage, setRowsPerPage] = useState(100);
  const [sorting, setSorting] = useState<any>(null);
  const [filtering, setFiltering] = useState<any>(null);
  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  const handleSourceTablePagination = (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
    filterData: any,
  ) => {
    setRowsPerPage(numPerPage);
    const data: any = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    setQueryParams(data);
    fetchSourcesTrigger(data)
      .unwrap()
      .then(() => {
        setSorting(sortData);
        setFiltering(filterData);
      })
      .catch(() => {
        handleSourceTablePagination(pageNumber, numPerPage, null, null);
      });
  };

  const handleSourceTableSorting = (sortData: any, filterData: any) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setQueryParams(data);
    fetchSourcesTrigger(data);
    setSorting(sortData);
    setFiltering(filterData);
  };

  const handleSourcesDownload = async () => {
    const sourceAll: any[] = [];
    if (!sourcesState || sourcesState.totalMatches === 0) {
      dispatch(showNotification("No sources to download", "warning"));
    } else {
      setDownloadProgressTotal(sourcesState.totalMatches);
      for (
        let i = 1;
        i <= Math.ceil(sourcesState.totalMatches / sourcesState.numPerPage);
        i += 1
      ) {
        const data: any = {
          ...filtering,
          pageNumber: i,
          numPerPage: sourcesState.numPerPage,
        };
        if (sorting) {
          data.sortBy = sorting.name;
          data.sortOrder = sorting.direction;
        }
        /* eslint-disable no-await-in-loop */
        try {
          const result: any = await fetchSourcesTrigger(data).unwrap();
          sourceAll.push(...result.sources);
          setDownloadProgressCurrent(sourceAll.length);
          setDownloadProgressTotal(sourcesState.totalMatches);
        } catch {
          // break the loop and set progress to 0 and show error message
          setDownloadProgressCurrent(0);
          setDownloadProgressTotal(0);
          if (sourceAll?.length === 0) {
            dispatch(
              showNotification(
                "Failed to fetch some sources. Download cancelled.",
                "error",
              ),
            );
          } else {
            dispatch(
              showNotification(
                "Failed to fetch some sources, please try again. Sources fetched so far will be downloaded.",
                "error",
              ),
            );
          }
          break;
        }
      }
    }
    setDownloadProgressCurrent(0);
    setDownloadProgressTotal(0);
    if (sourceAll?.length === sourcesState?.totalMatches) {
      dispatch(showNotification("Sources downloaded successfully"));
    }
    return sourceAll;
  };

  if (!sourceTableEmpty && !sourcesState?.sources) {
    return <Spinner />;
  }

  return (
    <>
      {sourceTableEmpty && (
        <div>
          <UninitializedDBMessage />
          <br />
        </div>
      )}
      {sourcesState?.sources ? (
        <SourceTable
          sources={sourcesState.sources}
          paginateCallback={handleSourceTablePagination}
          totalMatches={sourcesState.totalMatches}
          pageNumber={sourcesState.pageNumber}
          numPerPage={sourcesState.numPerPage}
          sortingCallback={handleSourceTableSorting}
          downloadCallback={handleSourcesDownload}
          fixedHeader={true}
        />
      ) : (
        <Spinner />
      )}
      <Dialog open={downloadProgressTotal > 0} maxWidth="md">
        <DialogContent
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <Typography variant="h6" display="inline">
            Downloading {downloadProgressTotal} sources
          </Typography>
          <div
            style={{
              height: "5rem",
              width: "5rem",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <ProgressIndicator
              current={downloadProgressCurrent}
              total={downloadProgressTotal}
              percentage={false}
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default SourceList;
