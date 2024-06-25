import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import NewAnalysisService from "../../NewAnalysisService";

import * as analysisServicesActions from "../../../ducks/analysis_services";
import AnalysisServiceList from "./AnalysisServiceList";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  paperContent: {
    padding: "1rem",
  },
  analysisServiceDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  analysisServiceDeleteDisabled: {
    opacity: 0,
  },
}));

/**
 * Main analysis service page showing the list of analysis services
 */
const AnalysisServicePage = () => {
  const { analysisServiceList } = useSelector(
    (state) => state.analysis_services,
  );

  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();
  const dispatch = useDispatch();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage Analysis Services");

  useEffect(() => {
    const getAnalysisServices = async () => {
      // Wait for the analysis services to update before setting
      // the new default form fields, so that the instruments list can
      // update

      await dispatch(analysisServicesActions.fetchAnalysisServices());
    };

    getAnalysisServices();
  }, [dispatch]);

  if (!analysisServiceList) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Analysis Services</Typography>
            <AnalysisServiceList
              analysisServices={analysisServiceList}
              deletePermission={permission}
            />
          </div>
        </Paper>
      </Grid>
      {permission && (
        <>
          <Grid item md={6} sm={12}>
            <Paper>
              <div className={classes.paperContent}>
                <Typography variant="h6">Add a New Analysis Service</Typography>
                <NewAnalysisService />
              </div>
            </Paper>
          </Grid>
        </>
      )}
    </Grid>
  );
};

AnalysisServiceList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  analysisServices: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
};

export default AnalysisServicePage;
