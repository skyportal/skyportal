import React, { useState, useEffect } from "react";
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

import { filterOutEmptyValues } from "../API";
import * as followupRequestActions from "../ducks/followup_requests";
import * as instrumentActions from "../ducks/instruments";
import Button from "./Button";

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
}));

const FollowupRequestSelectionForm = ({ fetchParams, setFetchParams }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { telescopeList } = useSelector((state) => state.telescopes);
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
  );
  const { followupRequestList } = useSelector(
    (state) => state.followup_requests
  );

  const defaultStartDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
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

  const sortedInstrumentList = [...instrumentList];
  sortedInstrumentList.sort((i1, i2) => {
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
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

  const handleSelectedFormatChange = (e) => {
    setSelectedFormat(e.target.value);
  };

  const handleSubmitFilter = async ({ formData }) => {
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
        "Start date must be before end date, please fix."
      );
    }
    return errors;
  }

  const FollowupRequestSelectionFormSchema = {
    type: "object",
    properties: {
      instrumentID: {
        type: "integer",
        oneOf: instrumentList.map((instrument) => ({
          enum: [instrument.id],
          title: `${
            telescopeList.find(
              (telescope) => telescope.id === instrument.telescope_id
            )?.name
          } / ${instrument.name}`,
        })),
        title: "Instrument",
        default: instrumentList[0]?.id,
      },
      startDate: {
        type: "string",
        format: "date-time",
        title: "Minimum Requested Date",
        description: "Do not include requests before this date",
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "Maximum Requested Date",
        description: "Do not include requests after this date",
      },
      sourceID: {
        type: "string",
        title: "Source ID [substrings acceptable]",
      },
      status: {
        type: "string",
        title: "Request status [completed, submitted, etc.]",
      },
      observationStartDate: {
        type: "string",
        format: "date-time",
        title: "Observation Start Date (Local Time)",
        default: defaultStartDate,
      },
      observationEndDate: {
        type: "string",
        format: "date-time",
        title: "Observation End Date (Local Time)",
        default: defaultEndDate,
      },
    },
  };

  const scheduleUrl = createScheduleUrl(
    selectedInstrumentId,
    selectedFormat,
    fetchParams
  );
  const reportUrl = createAllocationReportUrl(selectedInstrumentId);
  return (
    <div>
      <div data-testid="gcnsource-selection-form">
        <Form
          schema={FollowupRequestSelectionFormSchema}
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
      <div>
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
