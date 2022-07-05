import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/material-ui/v5";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import * as analysisServicesActions from "../ducks/analysis_services";
import * as sourceActions from "../ducks/source";
import GroupShareSelect from "./GroupShareSelect";

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
  Select: {
    width: "100%",
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

const LightcurveFitForm = ({ obj_id }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { analysisServiceList } = useSelector(
    (state) => state.analysis_services
  );

  const allGroups = useSelector((state) => state.groups.all);
  const [selectedAnalysisServiceId, setSelectedAnalysisServiceId] =
    useState(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const groupLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allGroups?.forEach((group) => {
    groupLookUp[group.id] = group;
  });

  const analysisServiceLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  analysisServiceList?.forEach((analysisService) => {
    analysisServiceLookUp[analysisService.id] = analysisService;
  });

  useEffect(() => {
    const getAnalysisServices = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the instruments list can
      // update

      const result = await dispatch(
        analysisServicesActions.fetchAnalysisServices()
      );

      const { data } = result;
      setSelectedAnalysisServiceId(data[0]?.id);
    };

    getAnalysisServices();
  }, [dispatch, setSelectedAnalysisServiceId]);

  if (
    !allGroups ||
    allGroups.length === 0 ||
    !analysisServiceList ||
    analysisServiceList.length === 0 ||
    !selectedAnalysisServiceId
  ) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const handleSubmit = async ({ formData }) => {
    setIsSubmitting(true);
    let params;
    if (selectedGroupIds.length === 0) {
      params = { analysis_parameters: formData };
    } else {
      params = { analysis_parameters: formData, group_ids: selectedGroupIds };
    }
    await dispatch(
      sourceActions.addAnalysisService(
        obj_id,
        selectedAnalysisServiceId,
        params
      )
    );
    setIsSubmitting(false);
  };

  const handleSelectedAnalysisServiceChange = (e) => {
    setSelectedAnalysisServiceId(e.target.value);
  };

  const OptionalParameters = {};
  if (
    analysisServiceLookUp[selectedAnalysisServiceId]
      ?.optional_analysis_parameters
  ) {
    const keys = Object.keys(
      analysisServiceLookUp[selectedAnalysisServiceId]
        .optional_analysis_parameters
    );
    keys.forEach((key) => {
      const params =
        analysisServiceLookUp[selectedAnalysisServiceId]
          ?.optional_analysis_parameters[key];
      OptionalParameters[key] = { type: "string", enum: params };
    });
  }

  const LightcurveFitSelectionFormSchema = {
    type: "object",
    properties: OptionalParameters,
    required: Object.keys(
      analysisServiceLookUp[selectedAnalysisServiceId]
        ?.optional_analysis_parameters
    ),
  };

  return (
    <div className={classes.container}>
      <div>
        <InputLabel id="analysisServiceSelectLabel">
          Analysis Service
        </InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="analysisServiceSelectLabel"
          value={selectedAnalysisServiceId || ""}
          onChange={handleSelectedAnalysisServiceChange}
          name="gcnPageInstrumentSelect"
          className={classes.Select}
        >
          {analysisServiceList?.map((analysisService) => (
            <MenuItem
              value={analysisService.id}
              key={analysisService.id}
              className={classes.SelectItem}
            >
              {analysisService.name}
            </MenuItem>
          ))}
        </Select>
      </div>
      <GroupShareSelect
        groupList={allGroups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
      <div data-testid="analysis-service-request-form">
        <div>
          <Form
            schema={LightcurveFitSelectionFormSchema}
            onSubmit={handleSubmit}
            // eslint-disable-next-line react/jsx-no-bind
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

LightcurveFitForm.propTypes = {
  obj_id: PropTypes.number.isRequired,
};

export default LightcurveFitForm;
