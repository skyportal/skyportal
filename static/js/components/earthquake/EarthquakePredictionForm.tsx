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

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import { useSubmitPredictionMutation } from "../../ducks/earthquake";
import * as mmadetectorActions from "../../ducks/mmadetector";
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
    marginBottom: "1rem",
    "& > *": {
      marginTop: "1rem",
      marginBottom: "1rem",
    },
  },
}));

interface EarthquakePredictionFormProps {
  earthquake: {
    event_id?: string;
    id?: number;
    [key: string]: any;
  };
}

const EarthquakePredictionForm = ({
  earthquake,
}: EarthquakePredictionFormProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [submitPrediction] = useSubmitPredictionMutation();

  const { mmadetectorList } = useAppSelector((state) => state["mmadetectors"]);
  const allGroups = useGetGroupsQuery().data?.all ?? null;
  const [selectedMMADetectorId, setSelectedMMADetectorId] = useState<any>(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const groupLookUp: Record<string, any> = {};

  allGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const mmadetectorLookUp: Record<string, any> = {};

  mmadetectorList?.forEach((mmadetector: any) => {
    mmadetectorLookUp[mmadetector.id] = mmadetector;
  });

  useEffect(() => {
    const getMMADetectors = async () => {
      // Wait for the mmadetectors to update before setting
      // the new default form fields, so that the mmadetectors list can
      // update

      const result: any = await dispatch(
        mmadetectorActions.mmadetectorApi.endpoints.getMMADetectors.initiate(),
      );

      const { data } = result;
      setSelectedMMADetectorId(data?.[0]?.id);
    };

    getMMADetectors();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
  }, [dispatch, setSelectedMMADetectorId, earthquake]);

  if (!allGroups || allGroups.length === 0 || mmadetectorList.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const handleSubmit = async ({ formData }: { formData: any }) => {
    if (!earthquake.event_id) {
      return;
    }
    setIsSubmitting(true);
    try {
      await submitPrediction({
        id: earthquake.event_id,
        mmadetector_id: selectedMMADetectorId,
        params: formData,
      }).unwrap();
    } catch {
      // error notification handled by the base query
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

    return errors;
  };

  const handleSelectedMMADetectorChange = (e: any) => {
    setSelectedMMADetectorId(e.target.value);
  };

  const EarthquakePredictionFormSchema = {
    type: "object",
    properties: {
      modelName: {
        type: "string",
        oneOf: [
          { enum: ["model1"], title: "Model 1" },
          { enum: ["model2"], title: "Model 2" },
          { enum: ["model3"], title: "Model 3" },
        ],
        default: "model1",
        title: "Model",
      },
    },
    required: ["modelName"],
  };

  return (
    <div className={classes.container}>
      <div>
        <InputLabel id="mmadetectorSelectLabel">MMADetector</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="mmadetectorSelectLabel"
          value={selectedMMADetectorId || ""}
          onChange={handleSelectedMMADetectorChange}
          name="earthquakeMMADetectorSelect"
          className={(classes as any).mmadetectorSelect}
        >
          {mmadetectorList?.map((mmadetector: any) => (
            <MenuItem
              value={mmadetector.id}
              key={mmadetector.id}
              className={(classes as any).mmadetectorSelectItem}
            >
              {`${mmadetector.name}`}
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
            schema={EarthquakePredictionFormSchema as any}
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

export default EarthquakePredictionForm;
