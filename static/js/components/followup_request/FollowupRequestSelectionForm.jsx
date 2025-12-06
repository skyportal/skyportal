import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import Divider from "@mui/material/Divider";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as followupRequestActions from "../../ducks/followupRequests";
import * as instrumentActions from "../../ducks/instruments";
import Button from "../Button";
import Spinner from "../Spinner";
import { utcString } from "../../utils/format";

dayjs.extend(utc);

const FollowupRequestSelectionForm = ({ fetchParams, setFetchParams }) => {
  const dispatch = useDispatch();
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments,
  );
  const { allocationListApiClassname } = useSelector(
    (state) => state.allocations,
  );
  const { users: allUsers } = useSelector((state) => state.users);
  const { followupRequestList } = useSelector(
    (state) => state.followupRequests,
  );
  const [isSubmittingFilter, setIsSubmittingFilter] = useState(false);
  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const [selectedFormat, setSelectedFormat] = useState("csv");
  const [includeStandards, setIncludeStandards] = useState(false);

  useEffect(() => {
    const getInstruments = async () => {
      const { data } = await dispatch(instrumentActions.fetchInstruments());
      setSelectedInstrumentId(data[0]?.id);
    };
    getInstruments();
  }, [dispatch, setSelectedInstrumentId]);

  if (
    !instrumentList.length ||
    !telescopeList.length ||
    !selectedInstrumentId ||
    !Object.keys(instrumentFormParams).length
  ) {
    return null;
  }

  if (!Array.isArray(followupRequestList)) return <Spinner />;

  const telLookUp = {};
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const sortedInstrumentList = [...instrumentList];
  // sort by telescope name, then by instrument name
  sortedInstrumentList.sort((i1, i2) => {
    const diff = telLookUp[i1.telescope_id].name.localeCompare(
      telLookUp[i2.telescope_id].name,
    );
    return diff !== 0 ? diff : i1.name.localeCompare(i2.name);
  });

  const instLookUp = {};
  sortedInstrumentList?.forEach((inst) => {
    instLookUp[inst.id] = inst;
  });

  const sortedAllocationListApiClassname = [...allocationListApiClassname];
  // sort by instrument name, then by allocation id
  sortedAllocationListApiClassname.sort((a1, a2) => {
    const instDiff = instLookUp[a1.instrument_id].name.localeCompare(
      instLookUp[a2.instrument_id].name,
    );
    return instDiff !== 0 ? instDiff : a1.id - a2.id;
  });

  const requestsGroupedByInstId = followupRequestList.reduce((r, a) => {
    r[a.allocation.instrument.id] = [
      ...(r[a.allocation.instrument.id] || []),
      a,
    ];
    return r;
  }, {});

  Object.values(requestsGroupedByInstId).forEach((value) => {
    value.sort();
  });
  // filter out allocations that are not of type triggered
  const filteredAllocationListApiClassname =
    sortedAllocationListApiClassname.filter((allocation) =>
      allocation.types.includes("triggered"),
    );
  // and only keep the instrument that has such allocations
  const filteredInstrumentList = sortedInstrumentList.filter((instrument) =>
    filteredAllocationListApiClassname.some(
      (allocation) => allocation.instrument_id === instrument.id,
    ),
  );

  const handleSubmitFilter = async () => {
    const {
      useObservationDates,
      observationStartDate,
      observationEndDate,
      filterby,
      instrumentID,
      allocationID,
      ...otherData
    } = fetchParams;

    const data = {
      includeObjThumbnails: false,
      ...(useObservationDates && {
        observationStartDate,
        observationEndDate,
      }),
      ...(filterby === "allocation" ? { allocationID } : { instrumentID }),
      ...otherData,
    };

    setIsSubmittingFilter(true);
    setSelectedInstrumentId(instrumentID);
    await dispatch(followupRequestActions.fetchFollowupRequests(data));
    setIsSubmittingFilter(false);
  };

  function handleDownloadSchedule() {
    // download the content and if status is 200 save it
    dispatch(
      followupRequestActions.downloadFollowupSchedule(
        selectedInstrumentId,
        selectedFormat,
        includeStandards,
      ),
    );
  }

  function handleDownloadAnalysis() {
    dispatch(
      followupRequestActions.downloadAllocationReport(selectedInstrumentId),
    );
  }

  function validateFilter(formData, errors) {
    if (formData.startDate > formData.endDate) {
      errors.startDate.addError(
        "Start date must be before end date, please fix.",
      );
    }
    return errors;
  }

  const FollowupRequestSelectionFormSchema = {
    type: "object",
    properties: {
      filterby: {
        type: "string",
        title: "Filter by",
        enum: ["instrument", "allocation"],
        default: "instrument",
      },
      startDate: {
        type: "string",
        format: "date-time",
        title: "Minimum Requested Date",
        description: "Do not include requests created before this date",
        default: utcString(dayjs().subtract(1, "day")),
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "Maximum Requested Date",
        description: "Do not include requests created after this date",
        default: utcString(dayjs().add(1, "day")),
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
        // pick users as requesters, and get their id
        type: "array",
        items: {
          type: "integer",
          enum: allUsers?.map((user) => user.id) || [],
        },
        uniqueItems: true,
        title: "Requester(s) (optional)",
      },
    },
    dependencies: {
      filterby: {
        oneOf: [
          {
            properties: {
              filterby: {
                enum: ["instrument"],
              },
              instrumentID: {
                type: "integer",
                oneOf: filteredInstrumentList.map((instrument) => ({
                  enum: [instrument.id],
                  title: `${
                    telescopeList.find(
                      (telescope) => telescope.id === instrument.telescope_id,
                    )?.name
                  } / ${instrument.name}`,
                })),
                title: "Instrument",
                default: filteredInstrumentList[0]?.id || null,
              },
            },
          },
          {
            properties: {
              filterby: {
                enum: ["allocation"],
              },
              allocationID: {
                type: "integer",
                oneOf: filteredAllocationListApiClassname.map((allocation) => ({
                  enum: [allocation.id],
                  // title should be instrument name [PI] (allocation id)
                  title: `${instLookUp[allocation.instrument_id]?.name} [${
                    allocation.pi
                  }] (${allocation.id})`,
                })),
                title: "Allocation",
                default: filteredAllocationListApiClassname[0]?.id || null,
              },
            },
          },
        ],
      },
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
      "ui:enumNames": allUsers?.map((user) => user.username) || [],
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
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box sx={{ position: "relative" }}>
        {isSubmittingFilter && (
          <CircularProgress
            sx={{ position: "absolute", top: "50%", left: "50%" }}
          />
        )}
        <Form
          formData={fetchParams}
          onChange={({ formData }) => setFetchParams(formData)}
          schema={FollowupRequestSelectionFormSchema}
          uiSchema={uiSchema}
          validator={validator}
          onSubmit={handleSubmitFilter}
          validate={validateFilter}
          disabled={isSubmittingFilter}
          liveValidate
        />
      </Box>
      <Divider>
        <Typography variant="h3">Schedule (with astroplan)</Typography>
      </Divider>
      <FormControl>
        <InputLabel id="instrumentSelectLabel">Format</InputLabel>
        <Select
          labelId="instrumentSelectLabel"
          label="Format"
          value={selectedFormat}
          onChange={(e) => setSelectedFormat(e.target.value)}
        >
          {["png", "pdf", "csv"].map((format) => (
            <MenuItem value={format} key={format}>
              {format.toUpperCase()}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <FormControlLabel
        label="Include Standards?"
        control={
          <Checkbox
            color="primary"
            title="Include Standards?"
            type="checkbox"
            onChange={(event) => setIncludeStandards(event.target.checked)}
            checked={includeStandards}
          />
        }
      />
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <Button primary onClick={handleDownloadSchedule}>
          Download
        </Button>
        <Button primary onClick={handleDownloadAnalysis}>
          Instrument Allocation Analysis
        </Button>
      </Box>
    </Box>
  );
};

FollowupRequestSelectionForm.propTypes = {
  fetchParams: PropTypes.shape({
    filterby: PropTypes.string,
    instrumentID: PropTypes.number,
    allocationID: PropTypes.number,
    startDate: PropTypes.string,
    endDate: PropTypes.string,
    observationStartDate: PropTypes.string,
    observationEndDate: PropTypes.string,
    sourceID: PropTypes.string,
    status: PropTypes.string,
    priorityThreshold: PropTypes.number,
    useObservationDates: PropTypes.bool,
    requesters: PropTypes.arrayOf(PropTypes.number),
  }).isRequired,
  setFetchParams: PropTypes.func.isRequired,
};

export default FollowupRequestSelectionForm;
