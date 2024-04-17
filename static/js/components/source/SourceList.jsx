import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";

import { showNotification } from "baselayer/components/Notifications";
import UninitializedDBMessage from "../UninitializedDBMessage";
import SourceTable from "./SourceTable";
import Spinner from "../Spinner";
import ProgressIndicator from "../ProgressIndicators";
import * as sourcesActions from "../../ducks/sources";

const SourceList = () => {
  const dispatch = useDispatch();

  const sourcesState = useSelector((state) => state.sources.latest);
  const sourceTableEmpty = useSelector(
    (state) => state.dbInfo.source_table_empty,
  );

  const [rowsPerPage, setRowsPerPage] = useState(100);
  const [sorting, setSorting] = useState(null);
  const [filtering, setFiltering] = useState(null);
  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  useEffect(() => {
    dispatch(sourcesActions.fetchSources());
  }, [dispatch]);

  const handleSourceTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData,
  ) => {
    setRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(sourcesActions.fetchSources(data)).then((response) => {
      if (response.status === "success") {
        setSorting(sortData);
        setFiltering(filterData);
      } else {
        handleSourceTablePagination(pageNumber, numPerPage, null, null);
      }
    });
  };

  const handleSourceTableSorting = (sortData, filterData) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(sourcesActions.fetchSources(data));
    setSorting(sortData);
    setFiltering(filterData);
  };

  const handleSourcesDownload = async () => {
    const sourceAll = [];
    if (sourcesState.totalMatches === 0) {
      dispatch(showNotification("No sources to download", "warning"));
    } else {
      setDownloadProgressTotal(sourcesState.totalMatches);
      for (
        let i = 1;
        i <= Math.ceil(sourcesState.totalMatches / sourcesState.numPerPage);
        i += 1
      ) {
        const data = {
          ...filtering,
          pageNumber: i,
          numPerPage: sourcesState.numPerPage,
        };
        if (sorting) {
          data.sortBy = sorting.name;
          data.sortOrder = sorting.direction;
        }
        /* eslint-disable no-await-in-loop */
        const result = await dispatch(sourcesActions.fetchSources(data));
        if (result && result.data && result?.status === "success") {
          sourceAll.push(...result.data.sources);
          setDownloadProgressCurrent(sourceAll.length);
          setDownloadProgressTotal(sourcesState.totalMatches);
        } else if (result && result?.status !== "success") {
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
    if (sourceAll?.length === sourcesState.totalMatches?.length) {
      dispatch(showNotification("Sources downloaded successfully"));
    }
    return sourceAll;
  };

  if (!sourceTableEmpty && !sourcesState.sources) {
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
          title="Sources"
          sources={sourcesState.sources}
          paginateCallback={handleSourceTablePagination}
          totalMatches={sourcesState.totalMatches}
          pageNumber={sourcesState.pageNumber}
          numPerPage={sourcesState.numPerPage}
          sortingCallback={handleSourceTableSorting}
          downloadCallback={handleSourcesDownload}
        />
      ) : (
        <Spinner />
      )}
      <Dialog
        open={downloadProgressTotal > 0}
        style={{ position: "fixed" }}
        maxWidth="md"
      >
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
