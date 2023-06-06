import React, { useEffect, useState, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import withRouter from "./withRouter";

import * as Action from "../ducks/instrument";

const Plot = React.lazy(() => import(/* webpackChunkName: "Bokeh" */ "./Plot"));

dayjs.extend(utc);

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

const InstrumentPlot = ({ instrumentId, startDate, endDate }) => {
  const plotWidth = 1600;
  const plot = (
    <Suspense
      fallback={
        <div>
          <CircularProgress color="secondary" />
        </div>
      }
    >
      <Plot
        url={`/api/internal/plot/instrument_log/${instrumentId}?width=${plotWidth}&height=500&startDate=${startDate}&endDate=${endDate}`}
      />
    </Suspense>
  );
  return plot;
};

InstrumentPlot.propTypes = {
  instrumentId: PropTypes.number.isRequired,
  startDate: PropTypes.string,
  endDate: PropTypes.string,
};

InstrumentPlot.defaultProps = {
  startDate: null,
  endDate: null,
};

const InstrumentSummary = ({ route }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const instrument = useSelector((state) => state.instrument);

  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);

  const defaultStartDate = dayjs
    .utc()
    .subtract(2, "day")
    .format("YYYY-MM-DD HH:mm:ss");
  const defaultEndDate = dayjs.utc().format("YYYY-MM-DD HH:mm:ss");

  // Load the instrument if needed
  useEffect(() => {
    dispatch(Action.fetchInstrument(route.id));
    setStartDate(defaultStartDate);
    setEndDate(defaultEndDate);
  }, [route.id, dispatch]);

  if (!("id" in instrument && instrument.id === parseInt(route.id, 10))) {
    // Don't need to do this for instruments -- we can just let the page be blank for a short time
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const handleSubmit = async ({ formData }) => {
    setStartDate(formData.startDate.replace("+00:00", "").replace(".000Z", ""));
    setEndDate(formData.endDate.replace("+00:00", "").replace(".000Z", ""));
  };

  const InstrumentSummaryFormSchema = {
    type: "object",
    properties: {
      startDate: {
        type: "string",
        format: "date-time",
        title: "Start Date",
        default: defaultStartDate,
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "End Date",
        default: defaultEndDate,
      },
    },
    required: ["startDate", "endDate"],
  };

  return (
    <div>
      <div className={styles.center}>
        {!instrument.log_exists ? (
          <div> No logs exist </div>
        ) : (
          <InstrumentPlot
            instrumentId={instrument.id}
            startDate={startDate}
            endDate={endDate}
          />
        )}
      </div>
      <div>
        <Form
          schema={InstrumentSummaryFormSchema}
          validator={validator}
          onSubmit={handleSubmit}
        />
      </div>
    </div>
  );
};

InstrumentSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.number,
  }).isRequired,
};

export default withRouter(InstrumentSummary);
