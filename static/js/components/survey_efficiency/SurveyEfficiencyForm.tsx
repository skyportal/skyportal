import { useGetGroupsQuery } from "../../ducks/groups";
import { useEffect, useState } from "react";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import * as surveyEfficiencyObservationsActions from "../../ducks/survey_efficiency_observations";
import * as surveyEfficiencyObservationPlansActions from "../../ducks/survey_efficiency_observation_plans";
import * as instrumentsActions from "../../ducks/instruments";
import { useGetAllocationsQuery } from "../../ducks/allocations";
import GroupShareSelect from "../group/GroupShareSelect";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  marginTop: {
    marginTop: "1rem",
  },
  allocationSelect: {
    width: "100%",
  },
  localizationSelect: {
    width: "100%",
  },
  fieldsToUseSelect: {
    width: "75%",
  },
  SelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
  },
}));

interface SurveyEfficiencyFormProps {
  gcnevent: {
    dateobs?: string;
    localizations?: Record<string, any>[];
    id?: number;
  };
  observationplanRequest?: {
    id?: number;
  } | null;
}

const SurveyEfficiencyForm = ({
  gcnevent,
  observationplanRequest = null,
}: SurveyEfficiencyFormProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: allocationList = [] } = useGetAllocationsQuery();

  const allGroups = useGetGroupsQuery().data?.all ?? null;
  const [selectedInstrumentId, setSelectedInstrumentId] = useState<any>(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const [selectedLocalizationId, setSelectedLocalizationId] =
    useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { instrumentList } = useAppSelector((state) => state["instruments"]);

  const instrumentsWithSensitivities = (instrumentList || []).filter(
    (i: any) => i.sensitivity_data,
  );

  const defaultStartDate = dayjs(gcnevent?.dateobs).format(
    "YYYY-MM-DDTHH:mm:ssZ",
  );
  const defaultEndDate = dayjs(gcnevent?.dateobs)
    .add(7, "day")
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const groupLookUp: Record<string, any> = {};

  allGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp: Record<string, any> = {};

  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp: Record<string, any> = {};

  allocationList?.forEach((allocation: any) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp: Record<string, any> = {};

  instrumentList?.forEach((instrumentObj: any) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const locLookUp: Record<string, any> = {};

  gcnevent.localizations?.forEach((loc: any) => {
    locLookUp[loc.id] = loc;
  });

  useEffect(() => {
    const getInstruments = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the instruments list can
      // update

      const result: any = await dispatch(instrumentsActions.fetchInstruments());

      const { data } = result;
      const newInstrumentsWithSensitivities = data.filter(
        (i: any) => i.sensitivity_data,
      );
      setSelectedInstrumentId(newInstrumentsWithSensitivities[0]?.id);
      setSelectedLocalizationId(gcnevent.localizations?.[0]?.["id"]);
    };
    if (!instrumentList || instrumentList.length === 0) {
      getInstruments();
    } else {
      setSelectedInstrumentId(instrumentsWithSensitivities[0]?.id);
      setSelectedLocalizationId(gcnevent?.localizations?.[0]?.["id"]);
    }

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedInstrumentId, setSelectedLocalizationId, gcnevent]);

  if (
    !allGroups ||
    allGroups.length === 0 ||
    telescopeList.length === 0 ||
    instrumentList.length === 0
  ) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const handleSelectedLocalizationChange = (e: any) => {
    setSelectedLocalizationId(e.target.value);
  };

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setIsSubmitting(true);
    if (!selectedLocalizationId) {
      dispatch(showNotification("No localization selected", "error"));
      setIsSubmitting(false);
      return;
    }
    if (!selectedInstrumentId) {
      dispatch(showNotification("No instrument selected", "error"));
      setIsSubmitting(false);
      return;
    }
    formData.startDate = formData.startDate
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.endDate = formData.endDate
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.localizationDateobs = locLookUp[selectedLocalizationId].dateobs;
    formData.localizationName = locLookUp[selectedLocalizationId].name;

    const optionalInjectionParameters: Record<string, any> = {};
    if (
      Object.keys(formData).includes("log10_E0") &&
      formData.log10_E0 !== undefined
    ) {
      optionalInjectionParameters["log10_E0"] = formData.log10_E0;
      delete formData.log10_E0;
    }
    if (Object.keys(formData).includes("mag") && formData.mag !== undefined) {
      optionalInjectionParameters["mag"] = formData.mag;
      delete formData.mag;
    }
    if (Object.keys(formData).includes("dmag") && formData.dmag !== undefined) {
      optionalInjectionParameters["dmag"] = formData.dmag;
      delete formData.dmag;
    }

    formData.optionalInjectionParameters = JSON.stringify(
      optionalInjectionParameters,
    );

    if (!observationplanRequest) {
      await dispatch(
        surveyEfficiencyObservationsActions.submitSurveyEfficiencyObservations(
          selectedInstrumentId,
          formData,
        ),
      );
    } else {
      await dispatch(
        surveyEfficiencyObservationPlansActions.submitSurveyEfficiencyObservationPlan(
          observationplanRequest.id!,
          formData,
        ),
      );
    }

    setIsSubmitting(false);
  };

  const validate = (formData: any, errors: any) => {
    if (
      formData.start_date &&
      formData.end_date &&
      formData.start_date > formData.end_date
    ) {
      errors.start_date.addError("Start Date must come before End Date");
    }

    const maxInjections = 100000;
    if (formData.numberInjections > maxInjections) {
      errors.numberInjections.addError(
        `Number of injections must be less than ${maxInjections}`,
      );
    }

    return errors;
  };

  const handleSelectedInstrumentChange = (e: any) => {
    setSelectedInstrumentId(e.target.value);
  };

  const SimSurveySelectionFormSchema: any = {
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
      numberInjections: {
        type: "integer",
        title: "Number of Injections",
        default: 1000,
      },
      numberDetections: {
        type: "integer",
        title: "Number of Detections",
        default: 1,
      },
      detectionThreshold: {
        type: "number",
        title: "Detection Threshold [sigma]",
        default: 5.0,
      },
      minimumPhase: {
        type: "number",
        title: "Minimum Phase [days]",
        default: 0.0,
      },
      maximumPhase: {
        type: "number",
        title: "Maximum Phase [days]",
        default: 3.0,
      },
      modelName: {
        type: "string",
        oneOf: [
          { enum: ["kilonova"], title: "Kilonova [GW170817-like]" },
          { enum: ["afterglow"], title: "GRB Afterglow" },
          { enum: ["linear"], title: "Linear model" },
        ],
        default: "kilonova",
        title: "Model",
      },
    },
    required: ["startDate", "endDate", "localizationCumprob"],
    dependencies: {
      modelName: {
        oneOf: [
          {
            properties: {
              modelName: {
                enum: ["afterglow"],
              },
              log10_E0: {
                type: "number",
                title: "log10(Energy [erg/s])",
                default: 53.0,
              },
            },
          },
          {
            properties: {
              modelName: {
                enum: ["linear"],
              },
              mag: {
                type: "number",
                title: "Peak magnitude",
                default: -16.0,
              },
              dmag: {
                type: "number",
                title: "Magnitude decay [1/day]",
                default: 1.0,
              },
            },
          },
        ],
      },
    },
  };

  return (
    <div className={classes.container}>
      <div>
        <InputLabel id="allocationSelectLabel">Localization</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="localizationSelectLabel"
          value={selectedLocalizationId || ""}
          onChange={handleSelectedLocalizationChange}
          name="observationPlanRequestLocalizationSelect"
          className={classes.localizationSelect}
        >
          {gcnevent.localizations?.map((localization: any) => (
            <MenuItem
              value={localization.id}
              key={localization.id}
              className={classes.SelectItem}
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
          className={(classes as any).instrumentSelect}
        >
          {instrumentsWithSensitivities?.map((instrument: any) => (
            <MenuItem
              value={instrument.id}
              key={instrument.id}
              className={(classes as any).instrumentSelectItem}
            >
              {`${telLookUp[instrument.telescope_id]?.name} / ${
                instrument.name
              }`}
            </MenuItem>
          ))}
        </Select>
      </div>
      <GroupShareSelect
        groupList={allGroups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
      <div data-testid="observationplan-request-form">
        <div>
          <Form
            schema={SimSurveySelectionFormSchema}
            validator={validator}
            onSubmit={handleSubmit as any}
            customValidate={validate}
            disabled={isSubmitting}
            liveValidate
          />
        </div>
        {isSubmitting && (
          <div className={classes.marginTop}>
            <CircularProgress />
          </div>
        )}
      </div>
    </div>
  );
};

export default SurveyEfficiencyForm;
