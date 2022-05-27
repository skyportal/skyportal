import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import Button from "@material-ui/core/Button";
import Form from "@rjsf/material-ui";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import CircularProgress from "@material-ui/core/CircularProgress";
import { makeStyles } from "@material-ui/core/styles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { filterOutEmptyValues } from "../API";
import * as followupRequestActions from "../ducks/followup_requests";
import * as instrumentActions from "../ducks/instruments";

dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  select: {
    width: "25%",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
  selectItem: {
    whiteSpace: "break-spaces",
  },
}));

const FollowupRequestSelectionForm = () => {
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

  const [formDataState, setFormDataState] = useState({
    observationStartDate: defaultStartDate,
    observationEndDate: defaultEndDate,
  });

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
    followupRequestList.length === 0 ||
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

  const handleSelectedInstrumentChange = (e) => {
    setSelectedInstrumentId(e.target.value);
  };

  const handleSelectedFormatChange = (e) => {
    setSelectedFormat(e.target.value);
  };

  const handleSubmitFilter = async ({ formData }) => {
    setIsSubmittingFilter(true);
    await dispatch(followupRequestActions.fetchFollowupRequests(formData));
    setFormDataState(formData);
    setIsSubmittingFilter(false);
  };

  function createUrl(instrumentId, format, queryParams) {
    let url = `/api/followup_request/schedule/${instrumentId}`;
    if (queryParams) {
      const filteredQueryParams = filterOutEmptyValues(queryParams);
      const queryString = new URLSearchParams(filteredQueryParams).toString();
      url += `?${queryString}`;
    }
    url += `&output_format=${format}`;
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

  const url = createUrl(selectedInstrumentId, selectedFormat, formDataState);
  return (
    <div>
      <div data-testid="gcnsource-selection-form">
        <Form
          schema={FollowupRequestSelectionFormSchema}
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
        <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="instrumentSelectLabel"
          value={selectedInstrumentId}
          onChange={handleSelectedInstrumentChange}
          name="followupRequestInstrumentSelect"
          className={classes.select}
        >
          {instrumentList?.map((instrument) => (
            <MenuItem
              value={instrument.id}
              key={instrument.id}
              className={classes.selectItem}
            >
              {`${telLookUp[instrument.telescope_id].name} / ${
                instrument.name
              }`}
            </MenuItem>
          ))}
        </Select>
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
        <Button
          href={`${url}`}
          download={`scheduleRequest-${selectedInstrumentId}`}
          size="small"
          color="primary"
          type="submit"
          variant="outlined"
          data-testid={`scheduleRequest_${selectedInstrumentId}`}
        >
          Download
        </Button>
      </div>
    </div>
  );
};

export default FollowupRequestSelectionForm;
