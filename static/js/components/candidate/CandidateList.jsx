import React, { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import ArrowUpward from "@mui/icons-material/ArrowUpward";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { ViewportList } from "react-viewport-list";

import { showNotification } from "baselayer/components/Notifications";
import FilterCandidateList from "./FilterCandidateList";
import Spinner from "../Spinner";
import Button from "../Button";

import * as candidatesActions from "../../ducks/candidates";
import CustomSortToolbar from "./CustomSortToolbar";
import Candidate from "./Candidate";

const numPerPage = 50;

const useStyles = makeStyles({
  listItem: {
    padding: 0,
    margin: 0,
    minWidth: "100%",
    display: "flex",
    flexDirection: "column",
  },
  spinnerDiv: {
    paddingTop: "2rem",
  },
  scrollContainer: {
    maxHeight: "calc(100vh - 12.5rem)",
    width: "100%",
    display: "flex",
    flexDirection: "column",
    overflowX: "hidden",
    overflowY: "auto",
  },
  backToTop: {
    marginTop: "1rem",
    display: "flex",
    justifyContent: "flex-end",
    minWidth: "100%",
    gap: "1rem",
  },
});

/**
 * Main candidate page showing the scanning interface.
 */
const CandidateList = () => {
  const ref = useRef(null);
  const [queryInProgress, setQueryInProgress] = useState(false);
  const [filterGroups, setFilterGroups] = useState([]);
  const classes = useStyles();
  const {
    candidates,
    pageNumber,
    totalMatches,
    queryID,
    selectedAnnotationSortOptions,
  } = useSelector((state) => state.candidates);

  const [sortOrder, setSortOrder] = useState(
    selectedAnnotationSortOptions ? selectedAnnotationSortOptions.order : null,
  );

  const { scanningProfiles } = useSelector(
    (state) => state.profile.preferences,
  );

  const defaultScanningProfile = scanningProfiles?.find(
    (profile) => profile.default,
  );

  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible,
  );

  const availableAnnotationsInfo = useSelector(
    (state) => state.candidates.annotationsInfo,
  );

  const filterFormData = useSelector(
    (state) => state.candidates.filterFormData,
  );

  const dispatch = useDispatch();

  useEffect(() => {
    // Grab the available annotation fields for filtering
    if (!availableAnnotationsInfo) {
      dispatch(candidatesActions.fetchAnnotationsInfo());
    }
  }, [dispatch, availableAnnotationsInfo]);

  useEffect(() => {
    if (defaultScanningProfile?.sortingOrder) {
      dispatch(
        candidatesActions.setCandidatesAnnotationSortOptions({
          origin: defaultScanningProfile.sortingOrigin,
          key: defaultScanningProfile.sortingKey,
          order: defaultScanningProfile.sortingOrder,
        }),
      );
      setSortOrder(defaultScanningProfile.sortingOrder);
    }
  }, [dispatch, defaultScanningProfile]);

  const groupIds = [];
  filterGroups?.forEach((g) => {
    groupIds.push(g.id);
  });

  const fetchPage = (offset) => {
    if (!queryInProgress && candidates?.length < totalMatches) {
      setQueryInProgress(true); // prevent multiple queries
      dispatch(showNotification("Loading more candidates..."));
      dispatch(
        candidatesActions.fetchCandidates({
          pageNumber: pageNumber + offset,
          numPerPage,
          queryID,
          filterGroups,
          sortOrder,
          annotationsInfo: availableAnnotationsInfo,
          filterFormData,
        }),
      ).then(() => {
        setQueryInProgress(false);
      });
    }
  };

  return (
    <div>
      <div>
        <FilterCandidateList
          userAccessibleGroups={userAccessibleGroups}
          setQueryInProgress={setQueryInProgress}
          setFilterGroups={setFilterGroups}
          numPerPage={numPerPage}
          annotationFilterList=""
          setSortOrder={setSortOrder}
        />
        <Box
          display={queryInProgress ? "block" : "none"}
          className={classes.spinnerDiv}
        >
          <Spinner />
        </Box>
        <Box style={{ marginTop: "0.75rem" }}>
          {queryInProgress ? (
            <div>
              <Spinner />
            </div>
          ) : (
            <div>
              <Paper
                variant="outlined"
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "1rem",
                }}
              >
                <div style={{ padding: "0.5rem 0.5rem 0.5rem 1rem" }}>
                  <Typography variant="h6">
                    Found {totalMatches} candidates.
                  </Typography>
                </div>
                <div style={{ display: "flex", flexDirection: "row" }}>
                  <CustomSortToolbar
                    filterGroups={filterGroups}
                    filterFormData={filterFormData}
                    setQueryInProgress={setQueryInProgress}
                    loaded={!queryInProgress}
                    sortOrder={sortOrder}
                    setSortOrder={setSortOrder}
                    numPerPage={numPerPage}
                  />
                </div>
              </Paper>
              <div className={classes.scrollContainer} ref={ref}>
                <ViewportList viewportRef={ref} count={candidates?.length || 0}>
                  {(index) => (
                    <div
                      key={candidates[index].id}
                      className={classes.listItem}
                    >
                      <Candidate
                        candidate={candidates[index]}
                        filterGroups={filterGroups}
                        index={index + (pageNumber - 1) * numPerPage + 1}
                        totalMatches={totalMatches}
                      />
                    </div>
                  )}
                </ViewportList>
              </div>
            </div>
          )}
        </Box>
      </div>
      <div className={classes.backToTop}>
        <Button
          primary
          onClick={() => {
            fetchPage(-1);
          }}
          size="small"
          disabled={pageNumber === 1 || queryInProgress}
        >
          <ArrowBackIcon />
          Previous
        </Button>
        <Button
          primary
          onClick={() => {
            fetchPage(1);
          }}
          size="small"
          disabled={pageNumber * numPerPage >= totalMatches || queryInProgress}
        >
          Next
          <ArrowForwardIcon />
        </Button>
        <Button
          primary
          onClick={() => {
            window.scrollTo({ top: 0 });
          }}
          size="small"
        >
          Back to top <ArrowUpward />
        </Button>
      </div>
    </div>
  );
};

export default CandidateList;
