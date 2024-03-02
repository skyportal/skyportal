import React, { useEffect, useState, useRef } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ArrowUpward from "@mui/icons-material/ArrowUpward";
import ArrowDownward from "@mui/icons-material/ArrowDownward";
import SortIcon from "@mui/icons-material/Sort";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Paper from "@mui/material/Paper";

import { showNotification } from "baselayer/components/Notifications";
import ThumbnailList from "./ThumbnailList";
import SaveCandidateButton from "./SaveCandidateButton";
import FilterCandidateList from "./FilterCandidateList";
import ScanningPageCandidateAnnotations, {
  getAnnotationValueString,
} from "./ScanningPageCandidateAnnotations";
import EditSourceGroups from "./EditSourceGroups";
import RejectButton from "./RejectButton";
import VegaPhotometry from "./VegaPhotometry";
import Spinner from "./Spinner";
import AddClassificationsScanningPage from "./AddClassificationsScanningPage";
import Button from "./Button";
import DisplayPhotStats from "./DisplayPhotStats";
import CandidatePlugins from "./CandidatePlugins";

import { ra_to_hours, dec_to_dms } from "../units";

import * as candidatesActions from "../ducks/candidates";

const numPerPage = 25;
const numPerPageOffset = 5;

const useStyles = makeStyles((theme) => ({
  listPaper: {
    borderColor: theme.palette.grey[350],
    borderWidth: "2px",
    marginBottom: "1rem",
  },
  listItem: {
    display: "grid",
    gridGap: "0.5rem",
    padding: "0.5rem",
    alignItems: "center",
    // we change the order of the children and the layout based on the screen size
    [theme.breakpoints.up("lg")]: {
      gridTemplateColumns: "5fr 2.5fr 4fr 3fr",
      gridTemplateAreas: `"thumbnails info photometry annotations"`,
    },
    [theme.breakpoints.down("lg")]: {
      gridTemplateAreas: `"thumbnails info" "photometry annotations"`,
      gridTemplateColumns: "5fr 3fr",
    },
    [theme.breakpoints.down("sm")]: {
      gridTemplateAreas: `"info" "thumbnails" "photometry" "annotations"`,
      gridTemplateColumns: "1fr",
    },
  },
  table: {
    marginTop: "1rem",
  },
  title: {
    marginBottom: "0.625rem",
  },
  pages: {
    margin: "1rem",
    "& > div": {
      display: "inline-block",
      margin: "1rem",
    },
  },
  spinnerDiv: {
    paddingTop: "2rem",
  },
  infoItem: {
    display: "flex",
    "& > span": {
      paddingLeft: "0.25rem",
      paddingBottom: "0.1rem",
    },
    flexFlow: "row wrap",
    paddingBottom: "0.25rem",
  },
  infoItemPadded: {
    "& > span": {
      paddingLeft: "0.25rem",
      paddingBottom: "0.1rem",
    },
    paddingBottom: "0.25rem",
  },
  saveCandidateButton: {
    margin: "0.25rem 0",
  },
  sortButtton: {
    "&:hover": {
      color: theme.palette.primary.main,
    },
  },
  chip: {
    margin: theme.spacing(0.2),
  },
  typography: {
    padding: theme.spacing(2),
  },
  helpButton: {
    display: "inline-block",
  },
  position: {
    fontWeight: "bold",
    fontSize: "105%",
  },
  formControl: {
    margin: theme.spacing(1),
    minWidth: 120,
  },
  formContainer: {
    display: "flex",
    flexFlow: "row wrap",
    alignItems: "center",
  },
  idButton: {
    textTransform: "none",
    marginBottom: theme.spacing(0.5),
    fontSize: "0.9rem",
  },
}));

const getMostRecentClassification = (classifications) => {
  // Display the most recent non-zero probability class
  const filteredClasses = classifications?.filter((i) => i.probability > 0);
  const sortedClasses = filteredClasses?.sort((a, b) =>
    a.modified < b.modified ? 1 : -1,
  );
  const recentClassification =
    sortedClasses?.length > 0 ? `${sortedClasses[0].classification}` : null;

  return recentClassification;
};

const CustomSortToolbar = ({
  filterGroups,
  filterFormData,
  setQueryInProgress,
  loaded,
  sortOrder,
  setSortOrder,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { selectedAnnotationSortOptions } = useSelector(
    (state) => state.candidates,
  );

  const handleSort = async () => {
    const newSortOrder =
      sortOrder === null || sortOrder === "desc" ? "asc" : "desc";
    setSortOrder(newSortOrder);

    setQueryInProgress(true);
    let data = {
      pageNumber: 1,
      numPerPage,
      groupIDs: filterGroups?.map((g) => g.id).join(),
      sortByAnnotationOrigin: selectedAnnotationSortOptions.origin,
      sortByAnnotationKey: selectedAnnotationSortOptions.key,
      sortByAnnotationOrder: newSortOrder,
    };
    if (filterFormData !== null) {
      data = {
        ...data,
        ...filterFormData,
      };
    }

    dispatch(
      candidatesActions.setCandidatesAnnotationSortOptions({
        ...selectedAnnotationSortOptions,
        order: newSortOrder,
      }),
    ).then(() => {
      dispatch(candidatesActions.fetchCandidates(data)).then(() => {
        setQueryInProgress(false);
      });
    });
  };

  // Wait until sorted data is received before rendering the toolbar
  return loaded ? (
    <Tooltip title="Sort on Selected Annotation">
      <span>
        <IconButton
          onClick={handleSort}
          disabled={selectedAnnotationSortOptions === null}
          className={classes.sortButtton}
          data-testid="sortOnAnnotationButton"
          size="large"
        >
          <>
            <SortIcon />
            {sortOrder !== null && sortOrder === "asc" && <ArrowUpward />}
            {sortOrder !== null && sortOrder === "desc" && <ArrowDownward />}
          </>
        </IconButton>
      </span>
    </Tooltip>
  ) : (
    <span />
  );
};

CustomSortToolbar.propTypes = {
  setQueryInProgress: PropTypes.func.isRequired,
  filterGroups: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
  filterFormData: PropTypes.shape({}),
  loaded: PropTypes.bool.isRequired,
  sortOrder: PropTypes.string,
  setSortOrder: PropTypes.func.isRequired,
};

CustomSortToolbar.defaultProps = {
  filterFormData: null,
  sortOrder: null,
};

const CandidateThumbnails = ({ sourceId }) => {
  const dispatch = useDispatch();

  const [ps1GenerationInProgressList, setPS1GenerationInProgressList] =
    useState([]);
  const generateSurveyThumbnail = (objID) => {
    setPS1GenerationInProgressList([...ps1GenerationInProgressList, objID]);
    dispatch(candidatesActions.generateSurveyThumbnail(objID)).then(() => {
      setPS1GenerationInProgressList(
        ps1GenerationInProgressList.filter((id) => id !== objID),
      );
    });
  };

  let candidateObj = null;
  const { candidates } = useSelector((state) => state.candidates);
  candidates?.forEach((candidate) => {
    if (candidate.id === sourceId) {
      candidateObj = { ...candidate };
    }
  });

  const hasPS1 = candidateObj?.thumbnails?.map((t) => t.type)?.includes("ps1");
  const displayTypes = hasPS1
    ? ["new", "ref", "sub", "sdss", "ls", "ps1"]
    : ["new", "ref", "sub", "sdss", "ls"];
  return (
    <div>
      {!candidateObj?.thumbnails ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(9rem, 1fr))",
              columnGap: 0,
              rowGap: "0.5rem",
              gridAutoFlow: "row",
            }}
          >
            <ThumbnailList
              ra={candidateObj.ra}
              dec={candidateObj.dec}
              thumbnails={candidateObj.thumbnails}
              minSize="6rem"
              size="100%"
              maxSize="8.8rem"
              titleSize="0.8rem"
              displayTypes={displayTypes}
              useGrid={false}
              noMargin
            />
          </div>
          {!hasPS1 && (
            <Button
              primary
              disabled={ps1GenerationInProgressList.includes(candidateObj.id)}
              size="small"
              onClick={() => {
                generateSurveyThumbnail(candidateObj.id);
              }}
              data-testid={`generatePS1Button${candidateObj.id}`}
            >
              Generate PS1 Cutout
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

CandidateThumbnails.propTypes = {
  sourceId: PropTypes.string.isRequired,
};

const CandidateInfo = ({
  sourceId,
  filterGroups,
  selectedAnnotationSortOptions,
}) => {
  const classes = useStyles();

  const allGroups = (useSelector((state) => state.groups.all) || []).filter(
    (g) => !g.single_user_group,
  );
  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible,
  );

  let candidateObj = null;
  const { candidates } = useSelector((state) => state.candidates);
  candidates?.forEach((candidate) => {
    if (candidate.id === sourceId) {
      candidateObj = { ...candidate };
    }
  });

  const candidateHasAnnotationWithSelectedKey = (obj) => {
    const annotation = obj.annotations.find(
      (a) => a.origin === selectedAnnotationSortOptions.origin,
    );
    if (annotation === undefined) {
      return false;
    }
    return selectedAnnotationSortOptions.key in annotation.data;
  };

  const getCandidateSelectedAnnotationValue = (obj) => {
    const annotation = obj.annotations.find(
      (a) => a.origin === selectedAnnotationSortOptions.origin,
    );
    return getAnnotationValueString(
      annotation.data[selectedAnnotationSortOptions.key],
    );
  };

  const recentHumanClassification =
    candidateObj.classifications && candidateObj.classifications.length > 0
      ? getMostRecentClassification(
          candidateObj.classifications.filter(
            (c) => c?.ml === false || c?.ml === null,
          ),
        )
      : null;

  const recentMLClassification =
    candidateObj.classifications && candidateObj.classifications.length > 0
      ? getMostRecentClassification(
          candidateObj.classifications.filter((c) => c?.ml === true),
        )
      : null;

  return (
    <div>
      {!candidateObj?.annotations ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div style={{ fontSize: "0.875rem", minWidth: "100%" }}>
          <span>
            <a
              href={`/source/${candidateObj.id}`}
              target="_blank"
              data-testid={candidateObj.id}
              rel="noreferrer"
            >
              <Button primary size="small" className={classes.idButton}>
                {candidateObj.id}&nbsp;
                <OpenInNewIcon fontSize="inherit" />
              </Button>
            </a>
          </span>
          {candidateObj.is_source ? (
            <div>
              <div>
                <Chip size="small" label="Previously Saved" color="primary" />
                <RejectButton objID={candidateObj.id} />
              </div>
              <div className={classes.infoItem}>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "row",
                    height: "1.6rem",
                    alignItems: "center",
                    gap: "0.1rem",
                  }}
                >
                  <b>Saved groups: </b>
                  <EditSourceGroups
                    source={{
                      id: candidateObj.id,
                      currentGroupIds: candidateObj.saved_groups?.map(
                        (g) => g.id,
                      ),
                    }}
                    groups={allGroups}
                    icon
                  />
                </div>
                <span>
                  {candidateObj.saved_groups?.map((group) => (
                    <Chip
                      label={
                        group.nickname
                          ? group.nickname.substring(0, 15)
                          : group.name.substring(0, 15)
                      }
                      key={group.id}
                      size="small"
                      className={classes.chip}
                    />
                  ))}
                </span>
              </div>
            </div>
          ) : (
            <div>
              <Chip size="small" label="NOT SAVED" />
              <RejectButton objID={candidateObj.id} />
            </div>
          )}
          {/* If candidate is either unsaved or is not yet saved to all groups being filtered on, show the "Save to..." button */}{" "}
          {Boolean(
            !candidateObj.is_source ||
              (candidateObj.is_source &&
                filterGroups?.filter(
                  (g) =>
                    !candidateObj.saved_groups
                      ?.map((x) => x.id)
                      ?.includes(g.id),
                ).length),
          ) && (
            // eslint-disable-next-line react/jsx-indent
            <div className={classes.saveCandidateButton}>
              <SaveCandidateButton
                candidate={candidateObj}
                userGroups={
                  // Filter out groups the candidate is already saved to
                  candidateObj.is_source
                    ? userAccessibleGroups?.filter(
                        (g) =>
                          !candidateObj.saved_groups
                            ?.map((x) => x.id)
                            ?.includes(g.id),
                      )
                    : userAccessibleGroups
                }
                filterGroups={
                  // Filter out groups the candidate is already saved to
                  candidateObj.is_source
                    ? filterGroups?.filter(
                        (g) =>
                          !candidateObj.saved_groups
                            ?.map((x) => x.id)
                            ?.includes(g.id),
                      )
                    : filterGroups
                }
              />
            </div>
          )}
          {candidateObj.last_detected_at && (
            <div className={classes.infoItem}>
              <b>Last detected: </b>
              <span>
                {
                  String(candidateObj.last_detected_at)
                    .split(".")[0]
                    .split("T")[1]
                }
                &nbsp;&nbsp;
                {
                  String(candidateObj.last_detected_at)
                    .split(".")[0]
                    .split("T")[0]
                }
              </span>
            </div>
          )}
          <div className={classes.infoItem}>
            <b>Coordinates: </b>
            <div>
              <span className={classes.position}>
                {ra_to_hours(candidateObj.ra)} &nbsp;
                {dec_to_dms(candidateObj.dec)}
              </span>
            </div>
            <div>
              (&alpha;,&delta;= {candidateObj.ra.toFixed(3)}, &nbsp;
              {candidateObj.dec.toFixed(3)})
            </div>
            <div>
              (l,b= {candidateObj.gal_lon.toFixed(3)}, &nbsp;
              {candidateObj.gal_lat.toFixed(3)})
            </div>
          </div>
          <div className={classes.infoItem}>
            <CandidatePlugins candidate={candidateObj} />
          </div>
          {candidateObj.photstats && (
            <div className={classes.infoItem}>
              <DisplayPhotStats
                photstats={candidateObj.photstats[0]}
                display_header
              />
            </div>
          )}
          <div className={classes.infoItemPadded}>
            <b>Latest Classification(s): </b>
            <div
              style={{
                display: "flex",
                flexFlow: "row wrap",
                alignItems: "center",
              }}
            >
              {recentHumanClassification && (
                <span>
                  <Chip
                    size="small"
                    label={recentHumanClassification}
                    color="primary"
                    className={classes.chip}
                  />
                </span>
              )}
              {recentMLClassification && (
                <span>
                  <Chip
                    size="small"
                    label={
                      <span
                        style={{
                          display: "flex",
                          direction: "row",
                          alignItems: "center",
                        }}
                      >
                        <Tooltip title="classification from an ML classifier">
                          <span>{`ML: ${recentMLClassification}`}</span>
                        </Tooltip>
                      </span>
                    }
                    className={classes.chip}
                  />
                </span>
              )}
              <AddClassificationsScanningPage obj_id={candidateObj.id} />
            </div>
          </div>
          {selectedAnnotationSortOptions !== null &&
            candidateHasAnnotationWithSelectedKey(candidateObj) && (
              <div className={classes.infoItem}>
                <b>
                  {selectedAnnotationSortOptions.key} (
                  {selectedAnnotationSortOptions.origin}):
                </b>
                <span>{getCandidateSelectedAnnotationValue(candidateObj)}</span>
              </div>
            )}
        </div>
      )}
    </div>
  );
};

CandidateInfo.propTypes = {
  sourceId: PropTypes.string.isRequired,
  filterGroups: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
  selectedAnnotationSortOptions: PropTypes.shape({
    origin: PropTypes.string.isRequired,
    key: PropTypes.string.isRequired,
    order: PropTypes.string,
  }),
};

CandidateInfo.defaultProps = {
  selectedAnnotationSortOptions: null,
};

const CandidatePhotometry = ({ sourceId }) => (
  <div>
    <VegaPhotometry
      sourceId={sourceId}
      style={{
        width: "70%",
        height: "100%",
        minHeight: "18rem",
        maxHeight: "18rem",
      }}
    />
  </div>
);

CandidatePhotometry.propTypes = {
  sourceId: PropTypes.string.isRequired,
};

const CandidateAutoannotations = ({ sourceId, filterGroups }) => {
  let candidateObj = null;
  const { candidates } = useSelector((state) => state.candidates);
  candidates?.forEach((candidate) => {
    if (candidate.id === sourceId) {
      candidateObj = { ...candidate };
    }
  });

  return (
    <div>
      {!candidateObj?.annotations ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div
          style={{
            overflowWrap: "break-word",
          }}
        >
          {candidateObj.annotations && (
            <ScanningPageCandidateAnnotations
              annotations={candidateObj.annotations}
              filterGroups={filterGroups || []}
            />
          )}
        </div>
      )}
    </div>
  );
};

CandidateAutoannotations.propTypes = {
  sourceId: PropTypes.string.isRequired,
  filterGroups: PropTypes.arrayOf(PropTypes.shape({})),
};

CandidateAutoannotations.defaultProps = {
  filterGroups: [],
};

const Candidate = React.memo(
  (props) => {
    const { sourceId, filterGroups, index, totalMatches } = props;
    const classes = useStyles();

    return (
      <Paper variant="outlined" className={classes.listPaper}>
        <div className={classes.listItem}>
          <div style={{ gridArea: "thumbnails" }}>
            <CandidateThumbnails sourceId={sourceId} />
          </div>
          <div style={{ gridArea: "info" }}>
            <CandidateInfo sourceId={sourceId} />
          </div>
          <div style={{ gridArea: "photometry" }}>
            <CandidatePhotometry sourceId={sourceId} />
          </div>
          <div
            style={{
              gridArea: "annotations",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              minHeight: "100%",
            }}
          >
            <CandidateAutoannotations
              sourceId={sourceId}
              filterGroups={filterGroups}
            />
            {/* here show a counter, saying this is candidate n/m */}
            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                paddingTop: "0.5rem",
              }}
            >
              <Typography fontWeight="bold">
                {`${index}/${totalMatches}`}
              </Typography>
            </div>
          </div>
        </div>
      </Paper>
    );
  },
  (prevProps, nextProps) =>
    prevProps.sourceId === nextProps.sourceId &&
    prevProps.filterGroups === nextProps.filterGroups &&
    prevProps.index === nextProps.index &&
    prevProps.totalMatches === nextProps.totalMatches,
);

Candidate.displayName = "Candidate";

Candidate.propTypes = {
  sourceId: PropTypes.string.isRequired,
  filterGroups: PropTypes.arrayOf(PropTypes.shape({})),
  index: PropTypes.number.isRequired,
  totalMatches: PropTypes.number.isRequired,
};

Candidate.defaultProps = {
  filterGroups: [],
};

const CandidateList = () => {
  const observerTarget = useRef(null);
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
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && candidates.length < totalMatches) {
          dispatch(showNotification("Loading more candidates..."));
          dispatch(
            candidatesActions.fetchCandidates(
              {
                pageNumber: pageNumber + 1,
                numPerPage,
                queryID,
                filterGroups,
                sortOrder,
                annotationsInfo: availableAnnotationsInfo,
                filterFormData,
              },
              true,
            ),
          );
        }
      },
      { threshold: 1 },
    );

    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }

    return () => {
      if (observerTarget.current) {
        observer.unobserve(observerTarget.current);
      }
    };
  }, [observerTarget, dispatch, queryInProgress, candidates]);

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

  const candidateIds = [];
  candidates?.forEach((candidate) => {
    candidateIds.push(candidate.id);
  });

  const groupIds = [];
  filterGroups?.forEach((g) => {
    groupIds.push(g.id);
  });

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
              {candidates?.length > 0 && (
                <Paper
                  variant="outlined"
                  style={{ display: "flex", justifyContent: "space-between" }}
                >
                  <div style={{ padding: "0.5rem" }}>
                    <Typography variant="h6">
                      Found {totalMatches} candidates (loaded:{" "}
                      {candidateIds?.length})
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
                    />
                  </div>
                </Paper>
              )}
              <List>
                {candidateIds?.map((candidateId, index) => (
                  <ListItem
                    key={candidateId}
                    style={{
                      padding: 0,
                      margin: 0,
                      minWidth: "100%",
                      display: "flex",
                      flexDirection: "column",
                    }}
                  >
                    <Candidate
                      sourceId={candidateId}
                      filterGroups={filterGroups}
                      index={index + 1}
                      totalMatches={totalMatches}
                    />
                    {totalMatches > 0 &&
                      candidates?.length < totalMatches &&
                      index === candidates?.length - numPerPageOffset - 1 && (
                        <div
                          style={{
                            minWidth: "100%",
                            height: "1px",
                          }}
                          ref={observerTarget}
                        />
                      )}
                  </ListItem>
                ))}
              </List>
            </div>
          )}
        </Box>
      </div>
      <div
        style={{
          marginTop: "1rem",
          display: "flex",
          justifyContent: "flex-end",
          minWidth: "100%",
        }}
      >
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
