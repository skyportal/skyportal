import React, { useEffect, Suspense, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

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
import Box from "@material-ui/core/Box";
import MUIDataTable from "mui-datatables";

import * as candidatesActions from "../ducks/candidates";
import ThumbnailList from "./ThumbnailList";
import CandidateCommentList from "./CandidateCommentList";
import SaveCandidateButton from "./SaveCandidateButton";
import FilterCandidateList from "./FilterCandidateList";

const VegaPlot = React.lazy(() =>
  import(/* webpackChunkName: "VegaPlot" */ "./VegaPlot")
);

const useStyles = makeStyles(() => ({
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
  infoItem: {
    display: "flex",
    "& > div": {
      paddingLeft: "0.25rem",
    },
    flexFlow: "row wrap",
  },
  saveCandidateButton: {
    margin: "0.5rem 0",
  },
  thumbnails: (props) => ({
    minWidth: props.thumbnailsMinWidth,
  }),
  info: {
    minWidth: 0,
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
        stackedHeader: {
          verticalAlign: "top",
        },
        stackedCommon: {
          [theme.breakpoints.down("sm")]: { width: "calc(75%)" },
          "&$stackedHeader": {
            width: "calc(25%)",
            overflowWrap: "break-word",
          },
        },
      },
    },
  });

const CandidateList = () => {
  const [queryInProgress, setQueryInProgress] = useState(false);
  // Maintain the three thumbnails in a row for larger screens
  const largeScreen = useMediaQuery((theme) => theme.breakpoints.up("md"));
  const thumbnailsMinWidth = largeScreen ? "27rem" : 0;
  const classes = useStyles({ thumbnailsMinWidth });
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

  const handleClickNextPage = async () => {
    setQueryInProgress(true);
    await dispatch(
      candidatesActions.fetchCandidates({ pageNumber: pageNumber + 1 })
    );
    setQueryInProgress(false);
  };

  const handleClickPreviousPage = async () => {
    setQueryInProgress(true);
    await dispatch(
      candidatesActions.fetchCandidates({ pageNumber: pageNumber - 1 })
    );
    setQueryInProgress(false);
  };

  const renderThumbnails = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <div className={classes.thumbnails}>
        <ThumbnailList
          ra={candidateObj.ra}
          dec={candidateObj.dec}
          thumbnails={candidateObj.thumbnails}
          size="8rem"
        />
      </div>
    );
  };

  const renderInfo = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <div className={classes.info}>
        <b>ID:</b>&nbsp;
        <Link to={`/candidate/${candidateObj.id}`}>{candidateObj.id}</Link>
        <br />
        {candidateObj.is_source ? (
          <div>
            <Link
              to={`/source/${candidateObj.id}`}
              style={{
                color: "red",
                texTableCellecoration: "underline",
              }}
            >
              Previously Saved
            </Link>
          </div>
        ) : (
          <div>
            NOT SAVED
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
            <div>
              {String(candidateObj.last_detected).split(".")[0].split("T")[1]}
            </div>
            <div>
              {String(candidateObj.last_detected).split(".")[0].split("T")[0]}
            </div>
          </div>
        )}
        <div className={classes.infoItem}>
          <b>Coordinates: </b>
          <div>{candidateObj.ra}</div>
          <div>{candidateObj.dec}</div>
        </div>
        <div className={classes.infoItem}>
          <b>Gal. Coords (l,b): </b>
          <div>{candidateObj.gal_lon.toFixed(3)}, </div>
          <div>{candidateObj.gal_lat.toFixed(3)}</div>
        </div>
        <br />
      </div>
    );
  };

  const renderPhotometry = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <Suspense fallback={<div>Loading plot...</div>}>
        <VegaPlot dataUrl={`/api/sources/${candidateObj.id}/photometry`} />
      </Suspense>
    );
  };

  const renderAutoannotations = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <div>
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
          handleClickNextPage={handleClickNextPage}
          handleClickPreviousPage={handleClickPreviousPage}
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
              }}
            />
          </MuiThemeProvider>
        </Box>
      </div>
      <div className={classes.pages}>
        <div>
          <Button
            variant="contained"
            onClick={handleClickPreviousPage}
            disabled={pageNumber === 1}
            size="small"
          >
            Previous Page
          </Button>
        </div>
        <div>
          <i>
            Displaying&nbsp;
            {numberingStart}-{numberingEnd}
            &nbsp; of&nbsp;
            {totalMatches}
            &nbsp; candidates.
          </i>
        </div>
        <div>
          <Button
            variant="contained"
            onClick={handleClickNextPage}
            disabled={lastPage}
            size="small"
          >
            Next Page
          </Button>
        </div>
      </div>
    </Paper>
  );
};

export default CandidateList;
