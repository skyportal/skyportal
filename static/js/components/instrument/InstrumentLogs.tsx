import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { useLazyGetInstrumentLogsQuery } from "../../ducks/instrument";
import { useLazyFetchInstrumentLogExternalQuery } from "../../ducks/instrument_log";
import { useGetAllocationsApiClassnameQuery } from "../../ducks/allocations";
import { useGetGroupsQuery } from "../../ducks/groups";
import Button from "../Button";
import Paper from "../Paper";
import InstrumentLogsPlot from "./InstrumentLogsPlot";

dayjs.extend(utc);

const INPUT_FORMAT = "YYYY-MM-DDTHH:mm";
const toParam = (value: string) =>
  dayjs.utc(value).format("YYYY-MM-DD HH:mm:ss");

interface InstrumentLogsProps {
  instrumentId: number;
  logExists: boolean;
}

const InstrumentLogs = ({ instrumentId, logExists }: InstrumentLogsProps) => {
  const [fetchLogs, { data: logs = [], isFetching: loading }] =
    useLazyGetInstrumentLogsQuery();
  const [fetchExternalLogs, { isFetching: retrieving }] =
    useLazyFetchInstrumentLogExternalQuery();
  const { data: allocations = [] } = useGetAllocationsApiClassnameQuery({
    instrument_id: instrumentId,
  });
  const groups = useGetGroupsQuery().data?.all ?? [];
  const [start, setStart] = useState(
    dayjs.utc().subtract(2, "day").format(INPUT_FORMAT),
  );
  const [end, setEnd] = useState(dayjs.utc().format(INPUT_FORMAT));
  const [pickedAllocationId, setPickedAllocationId] = useState<number>();
  const allocationId = pickedAllocationId ?? allocations[0]?.id;

  const invalidRange = !start || !end || start >= end;
  const params = { startDate: toParam(start), endDate: toParam(end) };
  const loadLogs = () => fetchLogs({ id: instrumentId, params });

  const retrieveLogs = async (id: number) => {
    const { error } = await fetchExternalLogs({ id, params });
    if (!error) loadLogs();
  };

  useEffect(() => {
    loadLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instrumentId]);

  return (
    <Paper sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 1.5,
        }}
      >
        <TextField
          type="datetime-local"
          size="small"
          label="Start (UTC)"
          value={start}
          onChange={(e) => setStart(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          type="datetime-local"
          size="small"
          label="End (UTC)"
          value={end}
          onChange={(e) => setEnd(e.target.value)}
          error={invalidRange}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <Button primary onClick={loadLogs} disabled={invalidRange || loading}>
          Show logs
        </Button>
        {allocationId !== undefined && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              ml: { md: "auto" },
            }}
          >
            <TextField
              select
              size="small"
              label="Allocation"
              value={allocationId}
              onChange={(e) => setPickedAllocationId(Number(e.target.value))}
              sx={{ minWidth: 220 }}
            >
              {allocations.map((allocation: any) => (
                <MenuItem key={allocation.id} value={allocation.id}>
                  {`${
                    groups.find((g) => g.id === allocation.group_id)?.name ??
                    "Allocation"
                  } (PI ${allocation.pi})`}
                </MenuItem>
              ))}
            </TextField>
            <Button
              secondary
              onClick={() => retrieveLogs(allocationId)}
              disabled={invalidRange || retrieving}
            >
              {retrieving ? "Retrieving..." : "Retrieve from facility"}
            </Button>
          </Box>
        )}
      </Box>
      {loading ? (
        <CircularProgress />
      ) : logs.length > 0 ? (
        <InstrumentLogsPlot instrument_logs={logs} />
      ) : (
        <Typography variant="body2" color="text.secondary">
          {logExists ? "No logs in this time range" : "No logs yet"}
        </Typography>
      )}
    </Paper>
  );
};

export default InstrumentLogs;
