import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import RefreshIcon from "@mui/icons-material/Refresh";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import React, { Suspense, useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";

import { Paper } from "@mui/material";
import IconButton from "@mui/material/IconButton";
import JsonDashboard from "react-json-dashboard";
import withRouter from "./withRouter";
import * as Action from "../ducks/instrument";
import InstrumentLogForm from "./InstrumentLogForm";

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
  columnItem: {
    marginBottom: theme.spacing(1),
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
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

  const refreshButton = (
    <IconButton
      color="primary"
      aria-label="refresh"
      style={{ margin: 0, padding: 0 }}
      onClick={() => {
        dispatch(Action.updateInstrumentStatus(route.id)).then((response) => {
          if (response.status === "success") {
            dispatch(showNotification("Instrument status updated"));
          } else {
            dispatch(
              showNotification("Error updating instrument status", "error"),
            );
          }
        });
      }}
    >
      <RefreshIcon />
    </IconButton>
  );

  return (
    <div>
      <Grid container spacing={2} className={styles.source}>
        <Grid item xs={12}>
          <div>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="instrument-log-content"
                id="instrument-log-header"
              >
                <Typography className={styles.accordionHeading}>
                  Instrument Log Display
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <div className={styles.columnItem}>
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
              </AccordionDetails>
            </Accordion>
          </div>
          <div>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="instrument-log-query"
                id="instrument-log-query"
              >
                <Typography className={styles.accordionHeading}>
                  Instrument Log Query
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <InstrumentLogForm instrument={instrument} />
              </AccordionDetails>
            </Accordion>
          </div>
          <Paper elevation={3} style={{ marginTop: "1rem", padding: "1rem" }}>
            <JsonDashboard
              title={`${instrument?.name || "Instrument"} Status`}
              data={instrument?.status || {}}
              lastUpdated={instrument?.last_status_update}
              refreshButton={refreshButton}
              showTitle
            />
          </Paper>
        </Grid>
      </Grid>
    </div>
  );
};

InstrumentSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.number,
  }).isRequired,
};

export default withRouter(InstrumentSummary);
