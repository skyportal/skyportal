import React, { useState } from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Toolbar from "@mui/material/Toolbar";
import Tooltip from "@mui/material/Tooltip";
import Grid from "@mui/material/Grid";
import Slide from "@mui/material/Slide";
import Paper from "@mui/material/Paper";
import makeStyles from "@mui/styles/makeStyles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Button from "../Button";

import { allowedClasses } from "../classification/ClassificationForm";
import ScanningProfilesList from "../ScanningProfilesList";
import CandidatesPreferencesForm from "./CandidatesPreferencesForm";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  dialogContent: {
    backgroundColor: theme.palette.background.default,
  },
  header: {
    justifyContent: "space-between",
  },
}));

// eslint-disable-next-line react/display-name
const Transition = React.forwardRef((props, ref) => (
  // eslint-disable-next-line react/jsx-props-no-spreading
  <Slide direction="up" ref={ref} {...props} />
));

const CandidatesPreferences = ({
  selectedScanningProfile,
  setSelectedScanningProfile,
}) => {
  const availableAnnotationsInfo = useSelector(
    (state) => state.candidates.annotationsInfo,
  );
  const classes = useStyles();

  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible,
  );

  // Get unique classification names, in alphabetical order
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);
  let classifications = [];
  latestTaxonomyList.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy)?.map(
      (option) => option.class,
    );
    classifications = classifications.concat(currentClasses);
  });
  classifications = Array.from(new Set(classifications)).sort();

  const [addDialogOpen, setAddDialogOpen] = useState(false);

  return (
    <div>
      <div>
        <Tooltip title="Save and load pre-set search options">
          <div>
            <Button
              secondary
              data-testid="manageScanningProfilesButton"
              onClick={() => {
                setAddDialogOpen(true);
              }}
            >
              Manage scanning profiles
            </Button>
          </div>
        </Tooltip>
      </div>
      <Dialog
        open={addDialogOpen}
        fullScreen
        onClose={() => {
          setAddDialogOpen(false);
        }}
        TransitionComponent={Transition}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <Toolbar className={classes.header}>
          <Typography variant="h6">Scanning Profiles</Typography>
          <IconButton
            edge="start"
            color="inherit"
            data-testid="closeScanningProfilesButton"
            onClick={() => {
              setAddDialogOpen(false);
            }}
            aria-label="close"
            size="large"
          >
            <CloseIcon />
          </IconButton>
        </Toolbar>
        <DialogContent className={classes.dialogContent}>
          <Grid container spacing={2}>
            <Grid item md={7} sm={12}>
              <ScanningProfilesList
                selectedScanningProfile={selectedScanningProfile}
                setSelectedScanningProfile={setSelectedScanningProfile}
                userAccessibleGroups={userAccessibleGroups}
                availableAnnotationsInfo={availableAnnotationsInfo}
                classifications={classifications}
              />
            </Grid>
            <Grid item md={5} sm={12}>
              <Paper>
                <CandidatesPreferencesForm
                  userAccessibleGroups={userAccessibleGroups}
                  availableAnnotationsInfo={availableAnnotationsInfo}
                  classifications={classifications}
                  addOrEdit="Add"
                  setSelectedScanningProfile={setSelectedScanningProfile}
                />
              </Paper>
            </Grid>
          </Grid>
        </DialogContent>
      </Dialog>
    </div>
  );
};

CandidatesPreferences.propTypes = {
  selectedScanningProfile: PropTypes.shape({}),
  setSelectedScanningProfile: PropTypes.func.isRequired,
};
CandidatesPreferences.defaultProps = {
  selectedScanningProfile: null,
};
export default CandidatesPreferences;
