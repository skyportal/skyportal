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

const AnalysisForm = ({ obj_id }) => {
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
    const analysis_parameters = {
      ...formData,
    };

    delete analysis_parameters.show_parameters;
    delete analysis_parameters.show_plots;
    delete analysis_parameters.show_corner;

    const params = {
      show_parameters: formData.show_parameters,
      show_plots: formData.show_plots,
      show_corner: formData.show_corner,
      analysis_parameters,
    };

    if (selectedGroupIds.length >= 0) {
      params.group_ids = selectedGroupIds;
    }
    await dispatch(
      sourceActions.startAnalysis(obj_id, selectedAnalysisServiceId, params)
    );
    setIsSubmitting(false);
  };

  const handleSelectedAnalysisServiceChange = (e) => {
    setSelectedAnalysisServiceId(e.target.value);
  };

  const OptionalParameters = {};
  const RequiredParameters = [];
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
      if (["True", "False"].every((val) => params.includes(val))) {
        OptionalParameters[key] = { type: "boolean" };
      } else {
        OptionalParameters[key] = { type: "string", enum: params };
        RequiredParameters.push(key);
      }
    });
  }

  const AnalysisSelectionFormSchema = {
    type: "object",
    properties: {
      ...OptionalParameters,
      show_parameters: {
        type: "boolean",
        title: "Show Parameters",
        description: "Whether to render the parameters of this analysis",
        default: false,
      },
      show_plots: {
        type: "boolean",
        title: "Show Plots",
        description: "Whether to render the plots of this analysis",
        default: false,
      },
      show_corner: {
        type: "boolean",
        title: "Show Corner",
        description: "Whether to render the corner of this analysis",
        default: false,
      },
    },
    required: ["show_parameters", "show_plots", "show_corner"].concat(
      RequiredParameters
    ),
  };

  return (
    <div className={classes.container}>
      <div>
        <InputLabel id="analysisServiceSelectLabel">
          Start New Analysis
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
            schema={AnalysisSelectionFormSchema}
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

AnalysisForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
};

export default AnalysisForm;
