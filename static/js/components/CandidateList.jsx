import React, { useEffect, Suspense, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useHistory } from "react-router-dom";

import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import {
  makeStyles,
  createMuiTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";
import useMediaQuery from "@material-ui/core/useMediaQuery";
import Button from "@material-ui/core/Button";
import CircularProgress from "@material-ui/core/CircularProgress";
import OpenInNewIcon from "@material-ui/icons/OpenInNew";
import ArrowUpward from "@material-ui/icons/ArrowUpward";
import Chip from "@material-ui/core/Chip";
import Box from "@material-ui/core/Box";
import MUIDataTable from "mui-datatables";

import * as candidatesActions from "../ducks/candidates";
import ThumbnailList from "./ThumbnailList";
import CandidateCommentList from "./CandidateCommentList";
import SaveCandidateButton from "./SaveCandidateButton";
import FilterCandidateList from "./FilterCandidateList";
import AddSourceGroup from "./AddSourceGroup";

const VegaPlot = React.lazy(() =>
  import(/* webpackChunkName: "VegaPlot" */ "./VegaPlot")
);

const useStyles = makeStyles((theme) => ({
  candidateListContainer: {
    padding: "1rem",
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
  itemPaddingBottom: {
    paddingBottom: "0.1rem",
  },
  infoItem: {
    display: "flex",
    "& > span": {
      paddingLeft: "0.25rem",
      paddingBottom: "0.1rem",
    },
    flexFlow: "row wrap",
  },
  saveCandidateButton: {
    margin: "0.5rem 0",
  },
  thumbnails: (props) => ({
    minWidth: props.thumbnailsMinWidth,
  }),
  info: (props) => ({
    fontSize: "0.875rem",
    minWidth: props.infoMinWidth,
    maxWidth: props.infoMaxWidth,
  }),
  annotations: (props) => ({
    minWidth: props.annotationsMinWidth,
  }),
  chip: {
    margin: theme.spacing(0.5),
  },
}));

// Hide built-in pagination and tweak responsive column widths
const getMuiTheme = (theme) =>
  createMuiTheme({
    overrides: {
      MUIDataTableFooter: {
        root: {
          display: "none",
        },
      },
      MUIDataTableBodyCell: {
        root: {
          padding: `${theme.spacing(1)}px ${theme.spacing(
            0.5
          )}px ${theme.spacing(1)}px ${theme.spacing(1)}px`,
        },
        stackedHeader: {
          verticalAlign: "top",
        },
        stackedCommon: {
          [theme.breakpoints.up("xs")]: { width: "calc(100%)" },
          "&$stackedHeader": {
            display: "none",
            overflowWrap: "break-word",
          },
        },
      },
    },
  });

const getMostRecentClassification = (classifications) => {
  // Display the most recent non-zero probability class
  const filteredClasses = classifications.filter((i) => i.probability > 0);
  const sortedClasses = filteredClasses.sort((a, b) =>
    a.modified < b.modified ? 1 : -1
  );

  return `${sortedClasses[0].classification}`;
};

const CandidateList = () => {
  const history = useHistory();
  const [queryInProgress, setQueryInProgress] = useState(false);
  // Maintain the three thumbnails in a row for larger screens
  const largeScreen = useMediaQuery((theme) => theme.breakpoints.up("md"));
  const thumbnailsMinWidth = largeScreen ? "30rem" : 0;
  const infoMinWidth = largeScreen ? "7rem" : 0;
  const infoMaxWidth = "14rem";
  const annotationsMinWidth = largeScreen ? "10rem" : 0;
  const classes = useStyles({
    thumbnailsMinWidth,
    infoMinWidth,
    infoMaxWidth,
    annotationsMinWidth,
  });
  const theme = useTheme();
  const {
    candidates,
    pageNumber,
    lastPage,
    totalMatches,
    numberingStart,
    numberingEnd,
  } = useSelector((state) => state.candidates);

  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible
  );

  const dispatch = useDispatch();

  useEffect(() => {
    if (candidates === null) {
      setQueryInProgress(true);
      dispatch(candidatesActions.fetchCandidates());
    } else {
      setQueryInProgress(false);
    }
  }, [candidates, dispatch]);

  const renderThumbnails = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <div className={classes.thumbnails}>
        <ThumbnailList
          ra={candidateObj.ra}
          dec={candidateObj.dec}
          thumbnails={candidateObj.thumbnails}
          size="9rem"
          displayTypes={["new", "ref", "sub", "sdss", "dr8"]}
        />
      </div>
    );
  };

  const renderInfo = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <div className={classes.info}>
        <span className={classes.itemPaddingBottom}>
          <b>ID:</b>&nbsp;
          <a
            href={`/candidate/${candidateObj.id}`}
            target="_blank"
            rel="noreferrer"
          >
            {candidateObj.id}&nbsp;
            <OpenInNewIcon fontSize="inherit" />
          </a>
        </span>
        <br />
        {candidateObj.is_source ? (
          <div>
            <div className={classes.itemPaddingBottom}>
              <Chip
                size="small"
                label="Previously Saved"
                clickable
                onClick={() => history.push(`/source/${candidateObj.id}`)}
                onDelete={() =>
                  window.open(`/source/${candidateObj.id}`, "_blank")
                }
                deleteIcon={<OpenInNewIcon />}
                color="primary"
              />
            </div>
            <div className={classes.saveCandidateButton}>
              <AddSourceGroup
                source={{
                  id: candidateObj.id,
                  currentGroupIds: candidateObj.saved_groups.map((g) => g.id),
                }}
                userGroups={userAccessibleGroups}
              />
            </div>
            <div className={classes.infoItem}>
              <b>Saved groups: </b>
              <span>
                {candidateObj.saved_groups.map((group) => (
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
            <Chip
              size="small"
              label="NOT SAVED"
              className={classes.itemPaddingBottom}
            />
            <br />
            <div className={classes.saveCandidateButton}>
              <SaveCandidateButton
                candidate={candidateObj}
                userGroups={userAccessibleGroups}
              />
            </div>
          </div>
        )}
        {candidateObj.last_detected && (
          <div className={classes.infoItem}>
            <b>Last detected: </b>
            <span>
              {String(candidateObj.last_detected).split(".")[0].split("T")[1]}
              &nbsp;&nbsp;
              {String(candidateObj.last_detected).split(".")[0].split("T")[0]}
            </span>
          </div>
        )}
        <div className={classes.infoItem}>
          <b>Coordinates: </b>
          <span>
            {candidateObj.ra}&nbsp;&nbsp;{candidateObj.dec}
          </span>
        </div>
        <div className={classes.infoItem}>
          <b>Gal. Coords (l,b): </b>
          <span>
            {candidateObj.gal_lon.toFixed(3)}&nbsp;&nbsp;
            {candidateObj.gal_lat.toFixed(3)}
          </span>
        </div>
        {candidateObj.classifications &&
          candidateObj.classifications.length > 0 && (
            <div className={classes.infoItem}>
              <b>Classification: </b>
              <span>
                {getMostRecentClassification(candidateObj.classifications)}
              </span>
            </div>
          )}
        <br />
      </div>
    );
  };

  const renderPhotometry = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <Suspense fallback={<CircularProgress />}>
        <VegaPlot dataUrl={`/api/sources/${candidateObj.id}/photometry`} />
      </Suspense>
    );
  };

  const renderAutoannotations = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <div className={classes.annotations}>
        {candidateObj.comments && (
          <CandidateCommentList comments={candidateObj.comments} />
        )}
      </div>
    );
  };

  const columns = [
    {
      name: "Images",
      label: "Images",
      options: {
        customBodyRenderLite: renderThumbnails,
      },
    },
    {
      name: "Info",
      label: "Info",
      options: {
        customBodyRenderLite: renderInfo,
      },
    },
    {
      name: "Photometry",
      label: "Photometry",
      options: {
        customBodyRenderLite: renderPhotometry,
      },
    },
    {
      name: "Autoannotations",
      label: "Autoannotations",
      options: {
        customBodyRenderLite: renderAutoannotations,
      },
    },
  ];

  return (
    <Paper elevation={1}>
      <div className={classes.candidateListContainer}>
        <Typography variant="h6" className={classes.title}>
          Scan candidates for sources
        </Typography>
        <FilterCandidateList
          userAccessibleGroups={userAccessibleGroups}
          pageNumber={pageNumber}
          numberingStart={numberingStart}
          numberingEnd={numberingEnd}
          lastPage={lastPage}
          totalMatches={totalMatches}
          setQueryInProgress={setQueryInProgress}
        />
        <Box
          display={queryInProgress ? "block" : "none"}
          className={classes.spinnerDiv}
        >
          <CircularProgress />
        </Box>
        <Box display={queryInProgress ? "none" : "block"}>
          <MuiThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              columns={columns}
              data={candidates !== null ? candidates : []}
              className={classes.table}
              options={{
                responsive: "vertical",
                filter: false,
                search: false,
                sort: false,
                print: false,
                download: false,
                selectableRows: "none",
                enableNestedDataAccess: ".",
                rowsPerPage: 25,
                rowsPerPageOptions: [10, 25, 100],
              }}
            />
          </MuiThemeProvider>
        </Box>
      </div>
      <div className={classes.pages}>
        <div>
          <Button
            variant="contained"
            onClick={() => {
              window.scrollTo({ top: 0 });
            }}
            size="small"
          >
            Back to top <ArrowUpward />
          </Button>
        </div>
      </div>
    </Paper>
  );
};

export default CandidateList;
