import { useEffect, useState } from "react";
import Form from "@rjsf/mui";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import RefreshIcon from "@mui/icons-material/Refresh";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";

import JsonDashboard from "react-json-dashboard";
import { Link } from "react-router-dom";
import withRouter from "../withRouter";
import { useAppDispatch } from "../../types/hooks";
import {
  useGetInstrumentQuery,
  useLazyGetInstrumentLogsQuery,
  useUpdateInstrumentStatusMutation,
} from "../../ducks/instrument";
import { useGetTelescopeQuery } from "../../ducks/telescopes";
import InstrumentLogForm from "./InstrumentLogForm";
import InstrumentLogsPlot from "./InstrumentLogsPlot";
import Paper from "../Paper";

dayjs.extend(utc);

interface InstrumentProps {
  route: {
    id: number;
  };
}

const Instrument = ({ route }: InstrumentProps) => {
  const dispatch = useAppDispatch();
  const { data: instrument } = useGetInstrumentQuery(route.id);
  const { data: telescope } = useGetTelescopeQuery(
    instrument?.["telescope_id"] as number,
    { skip: !instrument?.["telescope_id"] },
  );
  const [fetchInstrumentLogs] = useLazyGetInstrumentLogsQuery();
  const [updateInstrumentStatus] = useUpdateInstrumentStatusMutation();
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<any[] | undefined>(undefined);

  const defaultStartDate = dayjs
    .utc()
    .subtract(2, "day")
    .format("YYYY-MM-DD HH:mm:ss");
  const defaultEndDate = dayjs.utc().format("YYYY-MM-DD HH:mm:ss");

  // Load the instrument logs on mount.
  useEffect(() => {
    setLoading(true);
    fetchInstrumentLogs({
      id: route.id,
      params: {
        startDate: defaultStartDate,
        endDate: defaultEndDate,
      },
    })
      .unwrap()
      .then((response: any) => {
        setLogs(response);
      })
      .catch(() => {
        dispatch(showNotification("Error fetching instrument logs", "error"));
      })
      .finally(() => {
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route.id, dispatch]);

  if (instrument?.["id"] !== parseInt(route.id as any, 10)) {
    return <CircularProgress />;
  }

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setLoading(true);
    fetchInstrumentLogs({ id: route.id, params: formData })
      .unwrap()
      .then((response: any) => {
        setLogs(response);
      })
      .catch(() => {
        dispatch(showNotification("Error fetching instrument logs", "error"));
      })
      .finally(() => {
        setLoading(false);
      });
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
      onClick={async () => {
        try {
          await updateInstrumentStatus(route.id).unwrap();
          dispatch(showNotification("Instrument status updated"));
        } catch {
          dispatch(
            showNotification("Error updating instrument status", "error"),
          );
        }
      }}
    >
      <RefreshIcon />
    </IconButton>
  );

  return (
    <Grid container spacing={2}>
      <Grid size={12}>
        <Typography variant="h5">{instrument["name"]}</Typography>
        {telescope ? (
          <Link to={`/telescope/${instrument["telescope_id"]}`}>
            {telescope["name"]} ({telescope["nickname"]})
          </Link>
        ) : (
          <CircularProgress size={20} />
        )}
      </Grid>
      <Grid size={12}>
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h5">Instrument Log Display</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {loading ? (
              <CircularProgress />
            ) : !instrument["log_exists"] ? (
              "No logs exist"
            ) : !logs?.length ? (
              "No logs exist in the specified time range"
            ) : (
              <InstrumentLogsPlot instrument_logs={logs} />
            )}
            <Form
              schema={InstrumentSummaryFormSchema as any}
              validator={validator}
              onSubmit={handleSubmit as any}
            />
          </AccordionDetails>
        </Accordion>
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h5">Instrument Log Query</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <InstrumentLogForm
              instrument={instrument as { id: number; [key: string]: any }}
            />
          </AccordionDetails>
        </Accordion>
        <Paper>
          <JsonDashboard
            title={`${instrument?.["name"] || "Instrument"} Status`}
            data={instrument?.["status"] || {}}
            lastUpdated={instrument?.["last_status_update"]}
            refreshButton={refreshButton}
          />
        </Paper>
      </Grid>
    </Grid>
  );
};

export default withRouter(Instrument);
