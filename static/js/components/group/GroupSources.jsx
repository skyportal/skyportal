import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Paper from "@mui/material/Paper";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";

import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";

import SourceTable from "../source/SourceTable";
import withRouter from "../withRouter";
import ProgressIndicator from "../ProgressIndicators";

import * as sourcesActions from "../../ducks/sources";

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  source: {},
  commentListContainer: {
    height: "15rem",
    overflowY: "scroll",
    padding: "0.5rem 0",
  },
  tableGrid: {
    width: "100%",
  },
}));

const GroupSources = ({ route }) => {
  const dispatch = useDispatch();
  const savedSourcesState = useSelector(
    (state) => state.sources.savedGroupSources,
  );
  const pendingSourcesState = useSelector(
    (state) => state.sources.pendingGroupSources,
  );
  const groups = useSelector((state) => state.groups.userAccessible);
  const classes = useStyles();
  const [savedSourcesRowsPerPage, setSavedSourcesRowsPerPage] = useState(10);
  const [pendingSourcesRowsPerPage, setPendingSourcesRowsPerPage] =
    useState(10);
  const [sorting, setSorting] = useState(null);
  const [filtering, setFiltering] = useState(null);
  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  // Load the group sources
  useEffect(() => {
    const fetchData = async () => {
      await dispatch(
        sourcesActions.fetchSavedGroupSources({
          group_ids: [route.id],
          pageNumber: 1,
          numPerPage: 10,
        }),
      );
      await dispatch(
        sourcesActions.fetchPendingGroupSources({
          group_ids: [route.id],
          pageNumber: 1,
          numPerPage: 10,
        }),
      );
    };
    fetchData();
  }, [route.id, dispatch]);

  if (!savedSourcesState.sources || !pendingSourcesState.sources) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  const groupID = parseInt(route.id, 10);

  const groupName = groups?.filter((g) => g.id === groupID)[0]?.name || "";

  const handleSavedSourcesTableSorting = async (sortData, filterData) => {
    await dispatch(
      sourcesActions.fetchSavedGroupSources({
        ...filterData,
        group_ids: [route.id],
        pageNumber: 1,
        numPerPage: savedSourcesRowsPerPage,
        sortBy: sortData.name,
        sortOrder: sortData.direction,
      }),
    );
  };

  const handleSavedSourcesTablePagination = async (
    pageNumber,
    numPerPage,
    sortData,
    filterData,
  ) => {
    setSavedSourcesRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      group_ids: [route.id],
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    await dispatch(sourcesActions.fetchSavedGroupSources(data));
    setSorting(sortData);
    setFiltering(filterData);
  };

  const handlePendingSourcesTableSorting = async (sortData, filterData) => {
    await dispatch(
      sourcesActions.fetchPendingGroupSources({
        ...filterData,
        group_ids: [route.id],
        pageNumber: 1,
        numPerPage: pendingSourcesRowsPerPage,
        sortBy: sortData.name,
        sortOrder: sortData.direction,
      }),
    );
    setSorting(sortData);
    setFiltering(filterData);
  };

  const handlePendingSourcesTablePagination = async (
    pageNumber,
    numPerPage,
    sortData,
    filterData,
  ) => {
    setPendingSourcesRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      group_ids: [route.id],
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    await dispatch(sourcesActions.fetchPendingGroupSources(data));
  };

  const handleSourcesDownload = async () => {
    const sourceAll = [];
    if (savedSourcesState.totalMatches === 0) {
      await dispatch(showNotification("No sources to download", "warning"));
    } else {
      setDownloadProgressTotal(savedSourcesState.totalMatches);
      for (
        let i = 1;
        i <=
        Math.ceil(
          savedSourcesState.totalMatches / savedSourcesState.numPerPage,
        );
        i += 1
      ) {
        const data = {
          ...filtering,
          group_ids: [route.id],
          pageNumber: i,
          numPerPage: savedSourcesState.numPerPage,
        };
        if (sorting) {
          data.sortBy = sorting.name;
          data.sortOrder = sorting.direction;
        }
        /* eslint-disable no-await-in-loop */
        const result = await dispatch(
          sourcesActions.fetchSavedGroupSources(data),
        );
        if (result && result.data && result?.status === "success") {
          sourceAll.push(...result.data.sources);
          setDownloadProgressCurrent(sourceAll.length);
          setDownloadProgressTotal(savedSourcesState.totalMatches);
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
    if (sourceAll?.length === savedSourcesState.totalMatches?.length) {
      dispatch(showNotification("Sources downloaded successfully"));
    }
    return sourceAll;
  };

  return (
    <Paper elevation={1} className={classes.paper}>
      <div className={classes.source}>
        {!!savedSourcesState.sources && (
          <SourceTable
            sources={savedSourcesState.sources}
            title={`${groupName} sources`}
            sourceStatus="saved"
            groupID={groupID}
            paginateCallback={handleSavedSourcesTablePagination}
            pageNumber={savedSourcesState.pageNumber}
            totalMatches={savedSourcesState.totalMatches}
            numPerPage={savedSourcesState.numPerPage}
            sortingCallback={handleSavedSourcesTableSorting}
            downloadCallback={handleSourcesDownload}
          />
        )}
        <br />
        <br />
        {!!pendingSourcesState.sources && (
          <SourceTable
            sources={pendingSourcesState.sources}
            title="Requested to save"
            sourceStatus="requested"
            groupID={groupID}
            paginateCallback={handlePendingSourcesTablePagination}
            pageNumber={pendingSourcesState.pageNumber}
            totalMatches={pendingSourcesState.totalMatches}
            numPerPage={pendingSourcesState.numPerPage}
            sortingCallback={handlePendingSourcesTableSorting}
            downloadCallback={handleSourcesDownload}
          />
        )}
      </div>
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
    </Paper>
  );
};

GroupSources.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(GroupSources);
