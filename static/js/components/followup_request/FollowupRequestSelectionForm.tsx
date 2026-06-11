import { useState } from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import CircularProgress from "@mui/material/CircularProgress";
import { makeStyles } from "tss-react/mui";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Typography from "@mui/material/Typography";
import FormControl from "@mui/material/FormControl";
import Divider from "@mui/material/Divider";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

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

dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
  select: {
    width: "25%",
  },
  selectInstrument: {
    width: "99%",
  },
  selectItem: {
    whiteSpace: "break-spaces",
  },
}));

interface FollowupRequestSelectionFormProps {
  fetchParams: {
    pageNumber?: number;
    numPerPage?: number;
    observationStartDate?: string;
    observationEndDate?: string;
    [key: string]: any;
  };
  setFetchParams: (...a: any[]) => void;
}

const FollowupRequestSelectionForm = ({
  fetchParams,
  setFetchParams,
}: FollowupRequestSelectionFormProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentFormParams = {} } = useGetInstrumentFormsQuery();
  const { data: allocationListApiClassname = [] } =
    useGetAllocationsApiClassnameQuery();
  const allUsers = useGetUsersQuery().data?.users ?? [];
  const { data: followupRequestsData } =
    useGetFollowupRequestsQuery(fetchParams);
  const followupRequestList = followupRequestsData?.followup_requests;

  const defaultStartDate = dayjs()
    .subtract(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const [isSubmittingFilter, setIsSubmittingFilter] = useState(false);
  const [filterFormData, setFilterFormData] = useState<any>({
    filterby: "instrument",
    startDate: defaultStartDate,
    endDate: defaultEndDate,
    useObservationDates: false,
  });
  const [selectedInstrumentId, setSelectedInstrumentId] = useState<any>(null);
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

  const telLookUp: Record<string, any> = {};

  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const sortedInstrumentList = [...instrumentList];
  // sort by telescope name, then by instrument name
  sortedInstrumentList.sort((i1: any, i2: any) => {
    if (telLookUp[i1.telescope_id].name > telLookUp[i2.telescope_id].name) {
      return 1;
    }
    if (telLookUp[i2.telescope_id].name > telLookUp[i1.telescope_id].name) {
      return -1;
    }
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  const instLookUp: Record<string, any> = {};

  sortedInstrumentList?.forEach((inst: any) => {
    instLookUp[inst.id] = inst;
  });

  const sortedAllocationListApiClassname = [...allocationListApiClassname];
  // sort by instrument name, then by allocation id
  sortedAllocationListApiClassname.sort((a1: any, a2: any) => {
    if (instLookUp[a1.instrument_id].name > instLookUp[a2.instrument_id].name) {
      return 1;
    }
    if (instLookUp[a2.instrument_id].name > instLookUp[a1.instrument_id].name) {
      return -1;
    }
    if (a1.id > a2.id) {
      return 1;
    }
    if (a2.id > a1.id) {
      return -1;
    }
    return 0;
  });

  const requestsGroupedByInstId = followupRequestList.reduce(
    (r: Record<string, any[]>, a: any) => {
      r[a.allocation.instrument.id] = [
        ...(r[a.allocation.instrument.id] || []),
        a,
      ];
      return r;
    },
    {},
  );

  Object.values(requestsGroupedByInstId).forEach((value: any) => {
    value.sort();
  });
  // filter out allocations that are not of type triggered
  const filteredAllocationListApiClassname =
    sortedAllocationListApiClassname.filter((allocation: any) =>
      allocation.types.includes("triggered"),
    );
  // and only keep the instrument that have such allocations
  const filteredInstrumentList = sortedInstrumentList.filter(
    (instrument: any) =>
      filteredAllocationListApiClassname.some(
        (allocation: any) => allocation.instrument_id === instrument.id,
      ),
  );

  const handleSelectedFormatChange = (e: any) => {
    setSelectedFormat(e.target.value);
  };

  const handleSubmitFilter = async ({ formData }: { formData: any }) => {
    const data = { ...formData };
    data.includeObjThumbnails = false;
    if (data.useObservationDates === false) {
      delete data.observationStartDate;
      delete data.observationEndDate;
    }
    delete data.useObservationDates;
    if (data.filterby === "allocation") {
      delete data.instrumentID;
    } else {
      delete data.allocationID;
    }
    delete data.filterby;

    setIsSubmittingFilter(true);
    setFetchParams({
      ...data,
      pageNumber: 1,
      numPerPage: fetchParams.numPerPage,
      sortBy: fetchParams["sortBy"],
      sortOrder: fetchParams["sortOrder"],
    });
    setIsSubmittingFilter(false);
  };

  function handleDownloadSchedule(event: any) {
    if (!selectedInstrumentId) return;
    event.preventDefault(); // prevent the default form submission
    // we download the content here and then if status is 200 save it
    dispatch(
      downloadFollowupSchedule(
        selectedInstrumentId,
        selectedFormat,
        includeStandards,
      ),
    );
  }

  function handleDownloadAnalysis(event: any) {
    if (!selectedInstrumentId) return;
    event.preventDefault(); // prevent the default form submission
    dispatch(downloadAllocationReport(selectedInstrumentId));
  }

  function validateFilter(formData: any, errors: any) {
    if (formData.startDate > formData.endDate) {
      errors.startDate.addError(
        "Start date must be before end date, please fix.",
      );
    }
    return errors;
  }

  const instrumentOptions = filteredInstrumentList.map((instrument: any) => ({
    enum: [instrument.id],
    title: `${
      telescopeList.find(
        (telescope: any) => telescope.id === instrument.telescope_id,
      )?.["name"]
    } / ${instrument.name}`,
  }));
  const allocationOptions = filteredAllocationListApiClassname.map(
    (allocation: any) => ({
      enum: [allocation.id],
      title: `${instLookUp[allocation.instrument_id]?.name} [${
        allocation.pi
      }] (${allocation.id})`,
    }),
  );

  const FollowupRequestSelectionFormSchema: any = {
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
              ...(instrumentOptions.length > 0 && {
                enum: instrumentOptions.map((option: any) => option.enum[0]),
              }),
            },
          }
        : {
            allocationID: {
              type: "integer",
              title: "Allocation",
              ...(allocationOptions.length > 0 && {
                enum: allocationOptions.map((option: any) => option.enum[0]),
              }),
            },
          }),
      startDate: {
        type: "string",
        format: "date-time",
        title: "Minimum Requested Date",
        description: "Do not include requests created before this date",
        default: defaultStartDate,
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "Maximum Requested Date",
        description: "Do not include requests created after this date",
        default: defaultEndDate,
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
          // Only emit `enum` when there are users: ajv8 (rjsf v6) rejects an
          // empty `enum: []`, which fails the whole schema compile and prevents
          // every dependent field from rendering.
          ...(allUsers?.length
            ? { enum: allUsers.map((user: any) => user.id) }
            : {}),
        },
        uniqueItems: true,
        title: "Requester(s) (optional)",
      },
    },
    dependencies: {
      useObservationDates: {
        oneOf: [
          {
            properties: {
              useObservationDates: {
                enum: [false],
              },
            },
          },
          {
            properties: {
              useObservationDates: {
                enum: [true],
              },
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
      "ui:enumNames": allUsers?.map((user: any) => user.username) || [],
    },
    instrumentID: {
      "ui:enumNames": instrumentOptions.map((option: any) => option.title),
    },
    allocationID: {
      "ui:enumNames": allocationOptions.map((option: any) => option.title),
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
    <div>
      <Form
        formData={filterFormData}
        onChange={({ formData }: { formData: any }) =>
          setFilterFormData(formData)
        }
        schema={FollowupRequestSelectionFormSchema}
        uiSchema={uiSchema}
        validator={validator}
        onSubmit={handleSubmitFilter as any}
        {...({ validate: validateFilter } as any)}
        disabled={isSubmittingFilter}
        liveValidate
      />
      {isSubmittingFilter && <CircularProgress />}
      <Divider sx={{ my: 4 }} />
      <Typography variant="h6">Schedule (with astroplan)</Typography>
      <FormControl fullWidth>
        <InputLabel>Instrument</InputLabel>
        <Select
          label="Instrument"
          value={selectedInstrumentId ?? ""}
          onChange={(e) => setSelectedInstrumentId(e.target.value)}
          name="followupRequestInstrumentSelect"
          className={classes.selectInstrument}
        >
          {filteredInstrumentList.map((instrument: any) => (
            <MenuItem
              value={instrument.id}
              key={instrument.id}
              className={classes.selectItem}
            >
              {`${telLookUp[instrument.telescope_id]?.name} / ${
                instrument.name
              }`}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <InputLabel id="formatSelectLabel">Format</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="formatSelectLabel"
        value={selectedFormat}
        onChange={handleSelectedFormatChange}
        name="followupRequestFormatSelect"
        className={classes.select}
      >
        <MenuItem value="png" key="png" className={classes.selectItem}>
          PNG
        </MenuItem>
        <MenuItem value="pdf" key="pdf" className={classes.selectItem}>
          PDF
        </MenuItem>
        <MenuItem value="csv" key="csv" className={classes.selectItem}>
          CSV
        </MenuItem>
      </Select>
      <FormControlLabel
        label="Include Standards?"
        control={
          <Checkbox
            color="primary"
            title="Include Standards?"
            {...({ type: "checkbox" } as any)}
            onChange={(event) => setIncludeStandards(event.target.checked)}
            checked={includeStandards}
          />
        }
      />
      <Button
        primary
        size="small"
        type="submit"
        disabled={!selectedInstrumentId}
        onClick={handleDownloadSchedule}
      >
        Download
      </Button>
      <Button
        primary
        size="small"
        type="submit"
        disabled={!selectedInstrumentId}
        onClick={handleDownloadAnalysis}
      >
        Instrument Allocation Analysis
      </Button>
    </div>
  );
};

export default FollowupRequestSelectionForm;
