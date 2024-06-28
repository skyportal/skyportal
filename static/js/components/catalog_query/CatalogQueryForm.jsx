import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import * as allocationActions from "../../ducks/allocations";

import * as catalogQueryActions from "../../ducks/catalog_query";
import GroupShareSelect from "../group/GroupShareSelect";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
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

const CatalogQueryForm = ({ gcnevent }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationList } = useSelector((state) => state.allocations);

  const groups = useSelector((state) => state.groups.userAccessible);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [selectedLocalizationId, setSelectedLocalizationId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { instrumentList } = useSelector((state) => state.instruments);
  const { allocationListApiClassname } = useSelector(
    (state) => state.allocations,
  );

  const defaultStartDate = dayjs(gcnevent?.dateobs).format(
    "YYYY-MM-DDTHH:mm:ssZ",
  );
  const defaultEndDate = dayjs(gcnevent?.dateobs)
    .add(7, "day")
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const groupLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  groups?.forEach((group) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allocationList?.forEach((allocation) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const locLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  gcnevent.localizations?.forEach((loc) => {
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
      setSelectedLocalizationId(gcnevent.localizations[0]?.id);
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

  const handleSelectedLocalizationChange = (e) => {
    setSelectedLocalizationId(e.target.value);
  };

  const handleSubmit = async ({ formData }) => {
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

  const validate = (formData, errors) => {
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
        oneOf: allocationListApiClassname.map((allocation) => ({
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
          {gcnevent.localizations?.map((localization) => (
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
            schema={CatalogQueryFormSchema}
            validator={validator}
            onSubmit={handleSubmit}
            // eslint-disable-next-line react/jsx-no-bind
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

CatalogQueryForm.propTypes = {
  gcnevent: PropTypes.shape({
    dateobs: PropTypes.string,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      }),
    ),
    id: PropTypes.number,
  }).isRequired,
  observationplanRequest: PropTypes.shape({
    id: PropTypes.number,
  }),
};

CatalogQueryForm.defaultProps = {
  observationplanRequest: null,
};

export default CatalogQueryForm;
