import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import SmartToyTwoToneIcon from "@mui/icons-material/SmartToyTwoTone";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import Tooltip from "@mui/material/Tooltip";

import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
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
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
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

const StartBotSummary = ({ obj_id }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [dialogOpen, setDialogOpen] = useState(false);

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

    const params = {
      show_parameters: true,
      show_plots: false,
      show_corner: false,
      analysis_parameters,
    };

    if (selectedGroupIds.length >= 0) {
      params.group_ids = selectedGroupIds;
    }
    await dispatch(
      sourceActions.startAnalysis(obj_id, selectedAnalysisServiceId, params)
    );
    setIsSubmitting(false);
    setDialogOpen(false);
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

      if (Array.isArray(params)) {
        if (["True", "False"].every((val) => params.includes(val))) {
          OptionalParameters[key] = { type: "boolean" };
        } else {
          OptionalParameters[key] = { type: "string", enum: params };
          RequiredParameters.push(key);
        }
      } else if (typeof params === "object") {
        if (params?.type === "number") {
          OptionalParameters[key] = {
            type: "number",
            title: key,
          };
        } else if (params?.type === "file") {
          OptionalParameters[key] = {
            type: "string",
            format: "data-url",
            title: key,
            description: key, // we set a description by default for file as the title doesn't show up in the rjsf form
          };
        } else if (params?.type === "string") {
          OptionalParameters[key] = {
            type: "string",
            title: key,
          };
        }

        if (params?.default) {
          OptionalParameters[key].default = params.default;
        }

        if (params?.description) {
          OptionalParameters[key].description = params.description;
        }

        if (params?.title) {
          OptionalParameters[key].title = params.title;
        }

        if (params?.required) {
          if (["True", "true", "t"].includes(params.required)) {
            RequiredParameters.push(key);
          }
        }
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
    },
  };
  return (
    <>
      {analysisServiceList?.filter((service) => service.is_summary).length >
      0 ? (
        <Tooltip title="Start AI Summary">
          <SmartToyTwoToneIcon
            data-testid="runSummaryIconButton"
            fontSize="small"
            className={classes.editIcon}
            onClick={() => {
              setDialogOpen(true);
            }}
          />
        </Tooltip>
      ) : null}
      <Dialog
        open={dialogOpen}
        maxWidth="sm"
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Run AI Summary</DialogTitle>
        <DialogContent>
          <div>
            <InputLabel id="analysisServiceSelectLabel">
              Select AI Summary Service
            </InputLabel>
            <Select
              inputProps={{ MenuProps: { disableScrollLock: true } }}
              labelId="analysisServiceSelectLabel"
              value={selectedAnalysisServiceId || ""}
              onChange={handleSelectedAnalysisServiceChange}
              name="analysisServiceSelect"
              data-testid="analysisServiceSelect"
              className={classes.Select}
            >
              {analysisServiceList?.map(
                (analysisService) =>
                  analysisService.is_summary && (
                    <MenuItem
                      value={analysisService.id}
                      key={analysisService.id}
                      className={classes.SelectItem}
                    >
                      {analysisService.name}
                    </MenuItem>
                  )
              )}
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
                validator={validator}
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
        </DialogContent>
      </Dialog>
    </>
  );
};

StartBotSummary.propTypes = {
  obj_id: PropTypes.string.isRequired,
};

export default StartBotSummary;
