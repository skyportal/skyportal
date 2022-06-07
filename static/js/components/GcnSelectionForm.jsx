import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { PropTypes } from "prop-types";
import Button from "@material-ui/core/Button";
import Form from "@rjsf/material-ui";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import FormGroup from "@material-ui/core/FormGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Checkbox from "@material-ui/core/Checkbox";
import CircularProgress from "@material-ui/core/CircularProgress";
import { makeStyles } from "@material-ui/core/styles";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { filterOutEmptyValues } from "../API";
import * as sourcesActions from "../ducks/sources";
import * as observationsActions from "../ducks/observations";
import * as galaxiesActions from "../ducks/galaxies";
import * as instrumentsActions from "../ducks/instruments";

import LocalizationPlot from "./LocalizationPlot";

dayjs.extend(relativeTime);
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
  localizationSelect: {
    width: "100%",
  },
  localizationSelectItem: {
    whiteSpace: "break-spaces",
  },
  instrumentSelect: {
    width: "100%",
  },
  instrumentSelectItem: {
    whiteSpace: "break-spaces",
  },
}));

const GcnSelectionForm = ({ gcnEvent, setSelectedLocalizationName }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const displayOptions = [
    "localization",
    "sources",
    "galaxies",
    "instrument",
    "observations",
  ];
  const displayOptionsDefault = Object.fromEntries(
    displayOptions.map((x) => [x, false])
  );

  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const [selectedLocalizationId, setSelectedLocalizationId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmittingTreasureMap, setIsSubmittingTreasureMap] = useState(null);
  const [isDeletingTreasureMap, setIsDeletingTreasureMap] = useState(null);
  const [checkedDisplayState, setCheckedDisplayState] = useState(
    displayOptionsDefault
  );

  const defaultStartDate = dayjs(gcnEvent?.dateobs).format(
    "YYYY-MM-DDTHH:mm:ssZ"
  );
  const defaultEndDate = dayjs(gcnEvent?.dateobs)
    .add(7, "day")
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const [formDataState, setFormDataState] = useState({
    startDate: defaultStartDate,
    endDate: defaultEndDate,
  });

  const { telescopeList } = useSelector((state) => state.telescopes);

  const gcnEventSources = useSelector(
    (state) => state?.sources?.gcnEventSources
  );
  const gcnEventGalaxies = useSelector(
    (state) => state?.galaxies?.gcnEventGalaxies
  );

  const gcnEventObservations = useSelector(
    (state) => state?.observations?.gcnEventObservations
  );

  const gcnEventInstruments = useSelector(
    (state) => state?.instruments?.gcnEventInstruments
  );

  useEffect(() => {
    const getInstruments = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the instruments list can
      // update

      const result = await dispatch(
        instrumentsActions.fetchGcnEventInstruments(gcnEvent?.dateobs)
      );

      const { data } = result;
      setSelectedInstrumentId(data[0]?.id);
      setSelectedLocalizationId(gcnEvent.localizations[0]?.id);
      setSelectedLocalizationName(gcnEvent.localizations[0]?.localization_name);
    };

    getInstruments();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedInstrumentId, setSelectedLocalizationId, gcnEvent]);

  // need to check both of these conditions as selectedInstrumentId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if allocationList is not
  // empty.
  if (
    gcnEventInstruments.length === 0 ||
    !selectedInstrumentId ||
    gcnEvent.localizations.length === 0 ||
    !selectedLocalizationId
  ) {
    return <h3>Fetching skymap...</h3>;
  }

  const handleOnChange = (position) => {
    const checkedDisplayStateCopy = JSON.parse(
      JSON.stringify(checkedDisplayState)
    );
    checkedDisplayStateCopy[displayOptions[position]] =
      !checkedDisplayStateCopy[displayOptions[position]];
    setCheckedDisplayState(checkedDisplayStateCopy);
  };

  const handleSubmitTreasureMap = async (id, filterParams) => {
    setIsSubmittingTreasureMap(id);
    const data = {
      startDate: filterParams.startDate,
      endDate: filterParams.endDate,
      localizationCumprob: filterParams.localizationCumprob,
      localizationName: filterParams.localizationName,
      localizationDateobs: filterParams.localizationDateobs,
    };
    await dispatch(observationsActions.submitObservationsTreasureMap(id, data));
    setIsSubmittingTreasureMap(null);
  };

  const handleDeleteTreasureMap = async (id, filterParams) => {
    setIsDeletingTreasureMap(id);
    const data = {
      startDate: filterParams.startDate,
      endDate: filterParams.endDate,
      localizationCumprob: filterParams.localizationCumprob,
      localizationName: filterParams.localizationName,
      localizationDateobs: filterParams.localizationDateobs,
    };
    await dispatch(observationsActions.deleteObservationsTreasureMap(id, data));
    setIsDeletingTreasureMap(null);
  };

  const handleSubmit = async ({ formData }) => {
    setIsSubmitting(true);
    formData.startDate = formData.startDate
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.endDate = formData.endDate
      .replace("+00:00", "")
      .replace(".000Z", "");
    dispatch(sourcesActions.fetchGcnEventSources(gcnEvent.dateobs, formData));
    formData.includeGeoJSON = true;
    dispatch(
      observationsActions.fetchGcnEventObservations(gcnEvent.dateobs, formData)
    );
    dispatch(galaxiesActions.fetchGcnEventGalaxies(gcnEvent.dateobs, formData));
    dispatch(
      instrumentsActions.fetchGcnEventInstruments(gcnEvent.dateobs, formData)
    );
    setFormDataState(formData);
    setIsSubmitting(false);
  };

  // const handleSendToObservationPlan = (instrument) => {
  // const selectedFields = instrument?.fields.filter((f) => f?.selected);
  // const selectedIds = selectedFields.map((f) => f?.field_id);
  // };

  if (telescopeList.length === 0) {
    return <p>No robotic followup requests found...</p>;
  }

  if (
    !gcnEvent ||
    !gcnEventSources ||
    !gcnEventObservations ||
    !gcnEventGalaxies ||
    !gcnEventInstruments
  ) {
    return <CircularProgress />;
  }

  if (!gcnEvent.localizations || gcnEvent.localizations.length === 0) {
    return <p>No skymaps available to display...</p>;
  }

  const instLookUp = {};
  const instruments_with_contour = [];
  gcnEventInstruments?.forEach((instrument) => {
    if (instrument?.fields && instrument?.fields.length > 0) {
      instrument.fields.forEach((f) => {
        f.selected = false;
      });
      if (instrument.fields[0].contour_summary) {
        instruments_with_contour.push(instrument);
        instLookUp[instrument.id] = instrument;
      }
    }
  });

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const locLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  gcnEvent.localizations?.forEach((loc) => {
    locLookUp[loc.id] = loc;
  });

  const handleSelectedInstrumentChange = (e) => {
    setSelectedInstrumentId(e.target.value);
  };

  const handleSelectedLocalizationChange = (e) => {
    setSelectedLocalizationId(e.target.value);
    setSelectedLocalizationName(locLookUp[e.target.value].localization_name);
  };

  function createUrl(instrumentId, queryParams) {
    let url = `/api/observation/gcn/${instrumentId}`;
    if (queryParams) {
      const filteredQueryParams = filterOutEmptyValues(queryParams);
      const queryString = new URLSearchParams(filteredQueryParams).toString();
      url += `?${queryString}`;
    }
    return url;
  }

  function validate(formData, errors) {
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix."
      );
    }
    if (
      formData.localizationCumprob < 0 ||
      formData.localizationCumprob > 1.01
    ) {
      errors.cumulative.addError(
        "Value of cumulative should be between 0 and 1"
      );
    }
    return errors;
  }

  const url = createUrl(selectedInstrumentId, formDataState);
  const GcnSourceSelectionFormSchema = {
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
      localizationCumprob: {
        type: "number",
        title: "Cumulative Probability",
        default: 0.95,
      },
    },
    required: ["startDate", "endDate", "localizationCumprob"],
  };

  return (
    <div>
      {!(selectedLocalizationId in Object.entries(locLookUp)) ? (
        <div>
          <LocalizationPlot
            loc={gcnEvent.localizations[0]}
            sources={gcnEventSources}
            galaxies={gcnEventGalaxies}
            instrument={instLookUp[selectedInstrumentId]}
            observations={gcnEventObservations}
            options={checkedDisplayState}
          />
        </div>
      ) : (
        <div>
          <LocalizationPlot
            loc={locLookUp[selectedLocalizationId]}
            sources={gcnEventSources}
            galaxies={gcnEventGalaxies}
            instrument={instLookUp[selectedInstrumentId]}
            observations={gcnEventObservations}
            options={checkedDisplayState}
          />
        </div>
      )}
      <div>
        <Button
          variant="outlined"
          // onClick={() =>
          //   handleSendToObservationPlan(instLookUp[selectedInstrumentId])
          // }
        >
          Send selected to observation plan
        </Button>
        <InputLabel id="localizationSelectLabel">Localization</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="localizationSelectLabel"
          value={selectedLocalizationId || ""}
          onChange={handleSelectedLocalizationChange}
          name="gcnPageLocalizationSelect"
          className={classes.localizationSelect}
        >
          {gcnEvent.localizations?.map((localization) => (
            <MenuItem
              value={localization.id}
              key={localization.id}
              className={classes.localizationSelectItem}
            >
              {`${localization.localization_name}`}
            </MenuItem>
          ))}
        </Select>
      </div>
      <div>
        <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="instrumentSelectLabel"
          value={selectedInstrumentId || ""}
          onChange={handleSelectedInstrumentChange}
          name="gcnPageInstrumentSelect"
          className={classes.instrumentSelect}
        >
          {instruments_with_contour?.map((instrument) => (
            <MenuItem
              value={instrument.id}
              key={instrument.id}
              className={classes.instrumentSelectItem}
            >
              {`${telLookUp[instrument.telescope_id].name} / ${
                instrument.name
              }`}
            </MenuItem>
          ))}
        </Select>
      </div>
      <div>
        <FormGroup>
          {displayOptions.map((option, index) => (
            <FormControlLabel
              control={<Checkbox onChange={() => handleOnChange(index)} />}
              label={option}
              key={option}
            />
          ))}
        </FormGroup>
      </div>
      <div data-testid="gcnsource-selection-form">
        <Form
          schema={GcnSourceSelectionFormSchema}
          onSubmit={handleSubmit}
          // eslint-disable-next-line react/jsx-no-bind
          validate={validate}
          disabled={isSubmitting}
          liveValidate
        />
        {isSubmitting && (
          <div>
            <CircularProgress />
          </div>
        )}
      </div>
      <Button
        href={`${url}`}
        download={`observationGcn-${selectedInstrumentId}`}
        size="small"
        color="primary"
        type="submit"
        variant="outlined"
        data-testid={`observationGcn_${selectedInstrumentId}`}
      >
        GCN
      </Button>
      {isSubmittingTreasureMap === selectedInstrumentId ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div>
          <Button
            onClick={() => {
              handleSubmitTreasureMap(selectedInstrumentId, formDataState);
            }}
            size="small"
            color="primary"
            type="submit"
            variant="outlined"
            data-testid={`treasuremapRequest_${selectedInstrumentId}`}
          >
            Send to Treasure Map
          </Button>
        </div>
      )}
      {isDeletingTreasureMap === selectedInstrumentId ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div>
          <Button
            onClick={() => {
              handleDeleteTreasureMap(selectedInstrumentId, formDataState);
            }}
            size="small"
            color="primary"
            type="submit"
            variant="outlined"
            data-testid={`treasuremapDelete_${selectedInstrumentId}`}
          >
            Retract from Treasure Map
          </Button>
        </div>
      )}
    </div>
  );
};

GcnSelectionForm.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      })
    ),
    id: PropTypes.number,
  }).isRequired,
  setSelectedLocalizationName: PropTypes.func.isRequired,
};
export default GcnSelectionForm;
