import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";

import AllocationTable from "./AllocationTable";
import InstrumentTable from "./InstrumentTable";
import SkyCam from "./SkyCam";
import withRouter from "./withRouter";
import * as Action from "../ducks/telescope";

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  displayInlineBlock: {
    display: "inline-block",
  },
  center: {
    margin: "auto",
    padding: "0.625rem",
  },
  columnItem: {
    marginBottom: theme.spacing(1),
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
}));

const TelescopeSummary = ({ route }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const telescope = useSelector((state) => state.telescope);
  const instrumentsState = useSelector((state) => state.instruments);
  const groups = useSelector((state) => state.groups.all);

  // Load the instrument if needed
  useEffect(() => {
    dispatch(Action.fetchTelescope(route.id));
  }, [route.id, dispatch]);

  if (!("id" in telescope && telescope.id === parseInt(telescope.id, 10))) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <div>
      <Grid container spacing={2} className={styles.source}>
        <Grid
          item
          xs={12}
          sm={12}
          md={12}
          lg={4}
          xl={4}
          className={styles.displayInlineBlock}
        >
          <SkyCam telescope={telescope} />
        </Grid>
        <Grid item xs={12}>
          <div>
            <Typography variant="h6" display="inline">
              Instruments
            </Typography>
            {telescope.instruments && (
              <InstrumentTable
                instruments={telescope.instruments}
                telescopeInfo={false}
              />
            )}
          </div>
          <div>
            <Typography variant="h6" display="inline">
              Allocations
            </Typography>
            {telescope.allocations && (
              <AllocationTable
                instruments={instrumentsState.instrumentList}
                allocations={telescope.allocations}
                groups={groups}
                hideTitle
                telescopeInfo={false}
              />
            )}
          </div>
        </Grid>
      </Grid>
    </div>
  );
};

TelescopeSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.number,
  }).isRequired,
};

export default withRouter(TelescopeSummary);
