import { useState } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { useAppDispatch } from "../../types/hooks";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import {
  useGetFollowupRequestsQuery,
  downloadFollowupSchedule,
  downloadAllocationReport,
} from "../../ducks/followup_requests";
import {
  useGetInstrumentsQuery,
  useGetInstrumentFormsQuery,
} from "../../ducks/instruments";
import { useGetAllocationsApiClassnameQuery } from "../../ducks/allocations";
import { useGetUsersQuery } from "../../ducks/users";
import Button from "../Button";

const compareBy =
  (...keys: ((item: any) => any)[]) =>
  (a: any, b: any) => {
    for (const key of keys) {
      if (key(a) > key(b)) return 1;
      if (key(b) > key(a)) return -1;
    }
    return 0;
  };

interface FollowupRequestSelectionFormProps {
  fetchParams: Record<string, any>;
  setFetchParams: (params: Record<string, any>) => void;
}

const FollowupRequestSelectionForm = ({
  fetchParams,
  setFetchParams,
}: FollowupRequestSelectionFormProps) => {
  const dispatch = useAppDispatch();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentFormParams = {} } = useGetInstrumentFormsQuery();
  const { data: allocationListApiClassname = [] } =
    useGetAllocationsApiClassnameQuery();
  const allUsers = useGetUsersQuery().data?.users ?? [];
  const followupRequestList =
    useGetFollowupRequestsQuery(fetchParams).data?.followup_requests;

  const [filterFormData, setFilterFormData] = useState<any>({
    filterby: "instrument",
    useObservationDates: false,
  });
  const [selectedInstrumentId, setSelectedInstrumentId] = useState<any>("");
  const [selectedFormat, setSelectedFormat] = useState("csv");
  const [includeStandards, setIncludeStandards] = useState(false);

  if (!Array.isArray(followupRequestList)) return <CircularProgress />;
  if (
    !instrumentList.length ||
    !telescopeList.length ||
    !Object.keys(instrumentFormParams).length
  ) {
    return "No instruments or telescopes found...";
  }

  const telLookUp = Object.fromEntries(
    telescopeList.map((tel: any) => [tel.id, tel]),
  );
  const instLookUp = Object.fromEntries(
    instrumentList.map((inst: any) => [inst.id, inst]),
  );
  const instrumentName = (instrument: any) =>
    `${telLookUp[instrument.telescope_id]?.name} / ${instrument.name}`;

  const allocations = allocationListApiClassname
    .filter((allocation: any) => allocation.types.includes("triggered"))
    .sort(
      compareBy(
        (allocation) => instLookUp[allocation.instrument_id].name,
        (allocation) => allocation.id,
      ),
    );
  const instruments = [...instrumentList]
    .filter((instrument: any) =>
      allocations.some(
        (allocation) => allocation.instrument_id === instrument.id,
      ),
    )
    .sort(
      compareBy(
        (instrument) => telLookUp[instrument.telescope_id].name,
        (instrument) => instrument.name,
      ),
    );

  const handleSubmitFilter = ({ formData }: { formData?: any }) => {
    const {
      filterby,
      useObservationDates,
      observationStartDate,
      observationEndDate,
      instrumentID,
      allocationID,
      ...filters
    } = formData;
    setFetchParams({
      ...filters,
      ...(useObservationDates && { observationStartDate, observationEndDate }),
      ...(filterby === "allocation" ? { allocationID } : { instrumentID }),
      includeObjThumbnails: false,
      pageNumber: 1,
      numPerPage: fetchParams["numPerPage"],
      sortBy: fetchParams["sortBy"],
      sortOrder: fetchParams["sortOrder"],
    });
  };

  const schema: any = {
    type: "object",
    properties: {
      filterby: {
        type: "string",
        title: "Filter by",
        enum: ["instrument", "allocation"],
        default: "instrument",
      },
      ...(filterFormData.filterby === "instrument"
        ? {
            instrumentID: {
              type: "integer",
              title: "Instrument",
              ...(instruments.length && {
                enum: instruments.map(({ id }) => id),
              }),
            },
          }
        : {
            allocationID: {
              type: "integer",
              title: "Allocation",
              ...(allocations.length && {
                enum: allocations.map(({ id }) => id),
              }),
            },
          }),
      startDate: {
        type: "string",
        format: "date-time",
        title: "Minimum Requested Date",
        description: "Do not include requests created before this date",
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "Maximum Requested Date",
        description: "Do not include requests created after this date",
      },
      sourceID: {
        type: "string",
        title: "Source ID [substrings acceptable]",
      },
      status: {
        type: "string",
        title: "Request status [completed, submitted, etc.]",
      },
      priorityThreshold: {
        type: "number",
        title: "Only keep requests with priority above some value",
      },
      useObservationDates: {
        type: "boolean",
        title: "Filter on requests start and end dates?",
        default: false,
      },
      requesters: {
        type: "array",
        items: {
          type: "integer",
          ...(allUsers.length && { enum: allUsers.map(({ id }: any) => id) }),
        },
        uniqueItems: true,
        title: "Requester(s) (optional)",
      },
    },
    dependencies: {
      useObservationDates: {
        oneOf: [
          { properties: { useObservationDates: { enum: [false] } } },
          {
            properties: {
              useObservationDates: { enum: [true] },
              observationStartDate: {
                type: "string",
                format: "date-time",
                title: "Observation Start Date (Local Time)",
                description:
                  "Do not include requests with observations before this date",
              },
              observationEndDate: {
                type: "string",
                format: "date-time",
                title: "Observation End Date (Local Time)",
                description:
                  "Do not include requests with observations after this date",
              },
            },
          },
        ],
      },
    },
  };
  const uiSchema = {
    requesters: {
      "ui:enumNames": allUsers.map(({ username }: any) => username),
    },
    instrumentID: { "ui:enumNames": instruments.map(instrumentName) },
    allocationID: {
      "ui:enumNames": allocations.map(
        (allocation) =>
          `${instLookUp[allocation.instrument_id]?.name} [${allocation.pi}] (${allocation.id})`,
      ),
    },
    "ui:order": [
      "filterby",
      "instrumentID",
      "allocationID",
      "startDate",
      "endDate",
      "priorityThreshold",
      "useObservationDates",
      "observationStartDate",
      "observationEndDate",
      "sourceID",
      "status",
      "requesters",
    ],
  };

  return (
    <>
      <Form
        formData={filterFormData}
        onChange={({ formData }) => setFilterFormData(formData)}
        schema={schema}
        uiSchema={uiSchema}
        validator={validator}
        onSubmit={handleSubmitFilter}
        liveValidate
      />
      <Divider sx={{ my: 4 }} />
      <Typography variant="h6">Schedule (with astroplan)</Typography>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        <FormControl fullWidth>
          <InputLabel>Instrument</InputLabel>
          <Select
            label="Instrument"
            value={selectedInstrumentId}
            onChange={(e) => setSelectedInstrumentId(e.target.value)}
            name="followupRequestInstrumentSelect"
          >
            {instruments.map((instrument) => (
              <MenuItem
                value={instrument.id}
                key={instrument.id}
                sx={{ whiteSpace: "break-spaces" }}
              >
                {instrumentName(instrument)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <FormControl sx={{ minWidth: 120 }}>
            <InputLabel id="formatSelectLabel">Format</InputLabel>
            <Select
              inputProps={{ MenuProps: { disableScrollLock: true } }}
              labelId="formatSelectLabel"
              label="Format"
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value)}
              name="followupRequestFormatSelect"
            >
              <MenuItem value="png">PNG</MenuItem>
              <MenuItem value="pdf">PDF</MenuItem>
              <MenuItem value="csv">CSV</MenuItem>
            </Select>
          </FormControl>
          <FormControlLabel
            label="Include Standards?"
            control={
              <Checkbox
                checked={includeStandards}
                onChange={(e) => setIncludeStandards(e.target.checked)}
              />
            }
          />
        </Box>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            primary
            size="small"
            disabled={!selectedInstrumentId}
            onClick={() =>
              dispatch(
                downloadFollowupSchedule(
                  selectedInstrumentId,
                  selectedFormat,
                  includeStandards,
                ),
              )
            }
          >
            Download
          </Button>
          <Button
            primary
            size="small"
            disabled={!selectedInstrumentId}
            onClick={() =>
              dispatch(downloadAllocationReport(selectedInstrumentId))
            }
          >
            Instrument Allocation Analysis
          </Button>
        </Box>
      </Box>
    </>
  );
};

export default FollowupRequestSelectionForm;
