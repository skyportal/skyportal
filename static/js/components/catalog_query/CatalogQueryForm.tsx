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
import * as allocationActions from "../../ducks/allocations";

import * as catalogQueryActions from "../../ducks/catalog_query";
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

interface CatalogQueryFormProps {
  gcnevent: {
    dateobs?: string;
    localizations?: { id?: number; localization_name?: string }[];
    id?: number;
    [key: string]: any;
  };
  observationplanRequest?: { id?: number } | null;
}

const CatalogQueryForm = ({ gcnevent }: CatalogQueryFormProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  const { telescopeList } = useAppSelector((state) => state["telescopes"]);
  const { allocationList } = useAppSelector(
    (state) => state["allocations"],
  ) as any;

  const groups = useAppSelector((state) => state.groups.userAccessible);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const [selectedLocalizationId, setSelectedLocalizationId] =
    useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { instrumentList } = useAppSelector((state) => state["instruments"]);
  const { allocationListApiClassname } = useAppSelector(
    (state) => state["allocations"],
  ) as any;

  const defaultStartDate = dayjs(gcnevent?.dateobs).format(
    "YYYY-MM-DDTHH:mm:ssZ",
  );
  const defaultEndDate = dayjs(gcnevent?.dateobs)
    .add(7, "day")
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const groupLookUp: Record<string, any> = {};

  groups?.forEach((group: any) => {
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
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the instruments list can
      // update
      if (
        !allocationListApiClassname ||
        allocationListApiClassname?.length === 0
      ) {
        dispatch(allocationActions.fetchAllocationsApiClassname());
      }
      setSelectedLocalizationId(gcnevent.localizations?.[0]?.id);
    };

    getAllocations();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, gcnevent]);

  if (
    !groups ||
    groups.length === 0 ||
    telescopeList.length === 0 ||
    instrumentList.length === 0
  ) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  if (allocationListApiClassname.length === 0) {
    return <h3>No allocations with a follow-up API...</h3>;
  }

  const handleSelectedLocalizationChange = (e: any) => {
    setSelectedLocalizationId(e.target.value);
  };

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setIsSubmitting(true);

    const payload = {
      gcnevent_id: gcnevent.id,
      startDate: formData.startDate.replace("+00:00", "").replace(".000Z", ""),
      endDate: formData.endDate.replace("+00:00", "").replace(".000Z", ""),
      localizationDateobs: locLookUp[selectedLocalizationId].dateobs,
      localizationName: locLookUp[selectedLocalizationId].localization_name,
      localizationCumprob: formData.localizationCumprob,
      catalogName: formData.catalogName,
    };
    delete formData.startDate;
    delete formData.endDate;
    delete formData.localizationCumprob;
    delete formData.catalogName;

    formData.payload = payload;
    formData.target_group_ids = selectedGroupIds;

    await dispatch(catalogQueryActions.submitCatalogQuery(formData));

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

  const CatalogQueryFormSchema = {
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
      catalogName: {
        type: "string",
        oneOf: [
          { enum: ["LSXPS"], title: "Swift LSXPS catalog" },
          { enum: ["Gaia"], title: "Gaia" },
          { enum: ["TESS"], title: "TESS" },
          { enum: ["ZTF-Kowalski"], title: "ZTF Kowalski" },
          { enum: ["ZTF-Fink"], title: "ZTF Fink" },
        ],
        default: "LSXPS",
        title: "Catalog",
      },
      allocation_id: {
        type: "integer",
        oneOf: allocationListApiClassname.map((allocation: any) => ({
          enum: [allocation.id],
          title: `${
            telLookUp[instLookUp[allocation.instrument_id].telescope_id].name
          } / ${instLookUp[allocation.instrument_id].name} - ${
            groupLookUp[allocation.group_id]?.name
          } (PI ${allocation.pi})`,
        })),
        title: "Allocation",
        default: allocationListApiClassname[0]?.id,
      },
    },
    required: ["startDate", "endDate", "allocation_id", "catalogName"],
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
      <GroupShareSelect
        groupList={groups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
      <div data-testid="sourcequery-request-form">
        <div>
          <Form
            schema={CatalogQueryFormSchema as any}
            validator={validator}
            onSubmit={handleSubmit as any}
            customValidate={validate as any}
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

export default CatalogQueryForm;
