import React, { useEffect, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import CircularProgress from "@mui/material/CircularProgress";

import makeStyles from "@mui/styles/makeStyles";

import withRouter from "./withRouter";

import * as Action from "../ducks/instrument";

const Plot = React.lazy(() => import(/* webpackChunkName: "Bokeh" */ "./Plot"));

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
}));

const InstrumentSummary = ({ route }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const instrument = useSelector((state) => state.instrument);
  const plotWidth = 1600;

  // Load the instrument if needed
  useEffect(() => {
    dispatch(Action.fetchInstrument(route.id));
  }, [route.id, dispatch]);

  if (!("id" in instrument && instrument.id === parseInt(route.id, 10))) {
    // Don't need to do this for instruments -- we can just let the page be blank for a short time
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <div className={styles.center}>
      {!instrument.log_exists ? (
        <div> No logs exist </div>
      ) : (
        <Suspense
          fallback={
            <div>
              <CircularProgress color="secondary" />
            </div>
          }
        >
          <Plot
            url={`/api/internal/plot/instrument_log/${instrument.id}?width=${plotWidth}&height=500`}
          />
        </Suspense>
      )}
    </div>
  );
};

InstrumentSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.number,
  }).isRequired,
};

export default withRouter(InstrumentSummary);
