import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { Typography } from "@mui/material";
import { filterOutEmptyValues } from "../../API";
import * as followupRequestActions from "../../ducks/followup_requests";
import * as instrumentActions from "../../ducks/instruments";
import Button from "../Button";

dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  select: {
    width: "25%",
  },
  selectInstrument: {
    width: "99%",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
  selectItem: {
    whiteSpace: "break-spaces",
  },
  divider: {
    marginTop: "2rem",
    marginBottom: "1rem",
    minWidth: "100%",
    height: "2px",
    backgroundColor: "grey",
  },
}));

const FollowupRequestSelectionForm = ({ fetchParams, setFetchParams }) => {
  const classes = useStyles();
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
    (state) => state.followup_requests,
  );

  const defaultStartDate = dayjs()
    .subtract(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const [isSubmittingFilter, setIsSubmittingFilter] = useState(false);
  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const [selectedFormat, setSelectedFormat] = useState("csv");
  const [includeStandards, setIncludeStandards] = useState(false);

  useEffect(() => {
    const getInstruments = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(instrumentActions.fetchInstruments());

      const { data } = result;
      setSelectedInstrumentId(data[0]?.id);
    };

    getInstruments();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedInstrumentId]);

  if (!Array.isArray(followupRequestList)) {
    return <p>Waiting for followup requests to load...</p>;
  }

  if (
    instrumentList.length === 0 ||
    telescopeList.length === 0 ||
    !selectedInstrumentId ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <p>No robotic followup requests found...</p>;
  }

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const sortedInstrumentList = [...instrumentList];
  // sort by telescope name, then by instrument name
  sortedInstrumentList.sort((i1, i2) => {
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

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  sortedInstrumentList?.forEach((inst) => {
    instLookUp[inst.id] = inst;
  });

  const sortedAllocationListApiClassname = [...allocationListApiClassname];
  // sort by instrument name, then by allocation id
  sortedAllocationListApiClassname.sort((a1, a2) => {
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
  // and only keep the instrument that have such allocations
  const filteredInstrumentList = sortedInstrumentList.filter((instrument) =>
    filteredAllocationListApiClassname.some(
      (allocation) => allocation.instrument_id === instrument.id,
    ),
  );

  const handleSelectedFormatChange = (e) => {
    setSelectedFormat(e.target.value);
  };

  const handleSubmitFilter = async ({ formData }) => {
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
    setSelectedInstrumentId(formData.instrumentID);
    await dispatch(followupRequestActions.fetchFollowupRequests(formData));
    setFetchParams(formData);
    setIsSubmittingFilter(false);
  };

  function createScheduleUrl(instrumentId, format, queryParams) {
    let url = `/api/followup_request/schedule/${instrumentId}`;
    if (queryParams) {
      const filteredQueryParams = filterOutEmptyValues(queryParams);
      const queryString = new URLSearchParams(filteredQueryParams).toString();
      url += `?${queryString}`;
    }
    url += `&output_format=${format}&includeStandards=${includeStandards}`;
    return url;
  }

  function createAllocationReportUrl(instrumentId) {
    const url = `/api/allocation/report/${instrumentId}`;
    return url;
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
        // either instrument or allocation
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
        // pick users as requesters, and get their id
        type: "array",
        items: {
          type: "integer",
          anyOf: allUsers?.map((user) => ({
            enum: [user.id],
            type: "integer",
            title: user.username,
          })),
          title: "Requester(s) (optional)",
        },
        uniqueItems: true,
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

  const scheduleUrl = createScheduleUrl(
    selectedInstrumentId,
    selectedFormat,
    fetchParams,
  );
  const reportUrl = createAllocationReportUrl(selectedInstrumentId);
  return (
    <div>
      <div data-testid="followup-request-selection-form">
        <Form
          formData={fetchParams}
          onChange={({ formData }) => setFetchParams(formData)}
          schema={FollowupRequestSelectionFormSchema}
          uiSchema={uiSchema}
          validator={validator}
          onSubmit={handleSubmitFilter}
          // eslint-disable-next-line react/jsx-no-bind
          validate={validateFilter}
          disabled={isSubmittingFilter}
          liveValidate
        />
        {isSubmittingFilter && (
          <div>
            <CircularProgress />
          </div>
        )}
      </div>
      <div className={classes.divider} />
      <div>
        <Typography variant="h6">Schedule (with astroplan) </Typography>
        <InputLabel id="instrumentSelectLabel">Format</InputLabel>
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
              type="checkbox"
              onChange={(event) => setIncludeStandards(event.target.checked)}
              checked={includeStandards}
            />
          }
        />
        <Button
          primary
          href={`${scheduleUrl}`}
          download={`scheduleRequest-${selectedInstrumentId}`}
          size="small"
          type="submit"
          data-testid={`scheduleRequest_${selectedInstrumentId}`}
        >
          Download
        </Button>
        <Button
          primary
          href={`${reportUrl}`}
          download={`reportRequest-${selectedInstrumentId}`}
          size="small"
          type="submit"
          data-testid={`reportRequest_${selectedInstrumentId}`}
        >
          Instrument Allocation Analysis
        </Button>
      </div>
    </div>
  );
};

FollowupRequestSelectionForm.propTypes = {
  fetchParams: PropTypes.shape({
    pageNumber: PropTypes.number,
    numPerPage: PropTypes.number,
    observationStartDate: PropTypes.string,
    observationEndDate: PropTypes.string,
  }).isRequired,
  setFetchParams: PropTypes.func.isRequired,
};

export default FollowupRequestSelectionForm;
