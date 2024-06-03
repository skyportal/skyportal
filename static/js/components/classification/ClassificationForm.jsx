import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Input from "@mui/material/Input";
import InputLabel from "@mui/material/InputLabel";
import Chip from "@mui/material/Chip";
import makeStyles from "@mui/styles/makeStyles";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import * as Actions from "../../ducks/source";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
}));

// For each node in the hierarchy tree, add its full path from root
// to the nodePaths list
const addNodePaths = (nodePaths, hierarchy, prefix_path = []) => {
  const thisNodePath = [...prefix_path];

  if (
    hierarchy.class !== undefined &&
    hierarchy.class !== "Time-domain Source"
  ) {
    thisNodePath.push(hierarchy.class);
    nodePaths.push(thisNodePath);
  }

  hierarchy.subclasses?.forEach((item) => {
    if (typeof item === "object") {
      addNodePaths(nodePaths, item, thisNodePath);
    }
  });
};

// For each class in the hierarchy, return its name
// as well as the path from the root of hierarchy to that class
export const allowedClasses = (hierarchy) => {
  const classPaths = [];
  addNodePaths(classPaths, hierarchy);

  const classes = classPaths.map((path) => ({
    class: path.pop(),
    context: path.reverse(),
  }));

  return classes;
};

// Custom form widget for probability because rxjs MUI UpdownWidget does not have working min/max/step
// https://github.com/rjsf-team/react-jsonschema-form/issues/2022
const CustomProbabilityWidget = ({ value, onChange }) => (
  <TextField
    id="probability"
    label="Probability"
    type="number"
    helperText="[0-1]"
    InputLabelProps={{
      shrink: true,
    }}
    inputProps={{
      min: "0",
      max: "1",
      step: "0.0001",
    }}
    value={value || ""}
    onChange={(event) => {
      onChange(event.target.value);
    }}
  />
);
CustomProbabilityWidget.propTypes = {
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
};
CustomProbabilityWidget.defaultProps = {
  value: "",
};

const CustomGroupsWidget = ({ value, onChange, options }) => {
  const classes = useStyles();
  const groups = useSelector((state) => state.groups.userAccessible);

  const groupIDToName = {};
  groups?.forEach((g) => {
    groupIDToName[g.id] = g.name;
  });

  const ITEM_HEIGHT = 48;
  const MenuProps = {
    PaperProps: {
      style: {
        maxHeight: ITEM_HEIGHT * 4.5,
        width: 250,
      },
    },
  };
  return (
    <>
      <InputLabel id="classificationGroupSelectLabel">
        Choose Group (all groups if blank)
      </InputLabel>
      <Select
        id="groupSelect"
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        input={<Input id="selectGroupsChip" />}
        labelId="classificationGroupSelectLabel"
        value={value || ""}
        renderValue={(selected) => (
          <div className={classes.chips}>
            {selected?.map((group) => (
              <Chip
                key={group}
                label={groupIDToName[group]}
                className={classes.chip}
              />
            ))}
          </div>
        )}
        MenuProps={MenuProps}
        fullWidth
        multiple
      >
        {options.enumOptions.length > 0 &&
          options.enumOptions?.map((group) => (
            <MenuItem
              value={group.value}
              key={group.value.toString()}
              data-testid={`notificationGroupSelect_${group.value}`}
            >
              {group.label}
            </MenuItem>
          ))}
      </Select>
    </>
  );
};

CustomGroupsWidget.propTypes = {
  value: PropTypes.arrayOf(PropTypes.string).isRequired,
  onChange: PropTypes.func.isRequired,
  options: PropTypes.shape({
    enumOptions: PropTypes.arrayOf(PropTypes.shape({})),
  }).isRequired,
};

const ClassificationForm = ({ obj_id, taxonomyList }) => {
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);
  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);

  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);
  const [selectedFormData, setSelectedFormData] = useState({});

  const handleSubmit = async ({ formData }) => {
    setSubmissionRequestInProcess(true);
    // Get the classification without the context
    const classification = formData.classification.split(" <> ")[0];
    const data = {
      taxonomy_id: parseInt(formData.taxonomy, 10),
      obj_id,
      classification,
      probability: formData.probability,
      ml: formData.ml || false,
    };
    if (formData.groupIDs) {
      data.group_ids = formData.groupIDs?.map((id) => parseInt(id, 10));
    }
    const result = await dispatch(Actions.addClassification(data));
    setSubmissionRequestInProcess(false);
    if (result.status === "success") {
      dispatch(showNotification("Classification saved"));
    }
  };

  // Custom form widget for the classifications to format and display the contexts as well
  const CustomClassificationWidget = ({ value, onChange, options }) => {
    const filteringOptions = createFilterOptions({
      matchFrom: "start",
      stringify: (option) => option,
    });
    return (
      <Autocomplete
        id="classification"
        filterOptions={filteringOptions}
        options={options.enumOptions?.map((option) => option.value)}
        onChange={(event, newValue) => {
          onChange(newValue);
        }}
        value={value || ""}
        renderOption={(props, option) => {
          const [classification, context] = option.split(" <> ");
          return (
            <div {...props}>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  margin: "0.5rem",
                  marginTop: "0.25rem",
                  justifyContent: "center",
                  alignItems: "left",
                }}
                id={classification}
              >
                <b>{classification}</b>
                {context !== "" && <br />}
                {context}
              </div>
            </div>
          );
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Classification"
            variant="outlined"
            required
          />
        )}
      />
    );
  };

  CustomClassificationWidget.propTypes = {
    value: PropTypes.string,
    onChange: PropTypes.func.isRequired,
    options: PropTypes.shape({
      enumOptions: PropTypes.arrayOf(PropTypes.shape({})),
    }).isRequired,
  };

  CustomClassificationWidget.defaultProps = {
    value: "",
  };

  const widgets = {
    customClassificationWidget: CustomClassificationWidget,
    customProbabilityWidget: CustomProbabilityWidget,
    customGroupsWidget: CustomGroupsWidget,
  };

  const formSchema = {
    description: "Add Classification",
    type: "object",
    required: ["taxonomy", "classification", "probability"],
    properties: {
      groupIDs: {
        type: "array",
        items: {
          type: "string",
          anyOf: groups?.map((group) => ({
            enum: [group.id.toString()],
            type: "string",
            title: group.name,
          })),
        },
        uniqueItems: true,
      },
      taxonomy: {
        type: "string",
        title: "Taxonomy",
        anyOf: latestTaxonomyList?.map((taxonomy) => ({
          enum: [taxonomy.id.toString()],
          type: "string",
          title: `${taxonomy.name} (${taxonomy.version})`,
        })),
      },
    },
    dependencies: {
      taxonomy: {
        oneOf: [],
      },
    },
  };
  latestTaxonomyList?.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy).map(
      (option) =>
        `${option.class} <> ${
          option.context.length > 0 ? option.context.join(" « ") : ""
        }`,
    );
    formSchema.dependencies.taxonomy.oneOf.push({
      properties: {
        taxonomy: {
          enum: [taxonomy.id.toString()],
        },
        classification: {
          type: "string",
          name: "classification",
          title: "Classification",
          enum: currentClasses,
        },
        probability: {
          type: "number",
          name: "probability",
          title: "Probability",
        },
        ml: {
          type: "boolean",
          name: "ml",
          title: "ML based classification?",
        },
      },
    });
  });
  const uiSchema = {
    groupIDs: { "ui:widget": "customGroupsWidget" },
    classification: { "ui:widget": "customClassificationWidget" },
    probability: { "ui:widget": "customProbabilityWidget" },
  };

  const validate = (formData, errors) => {
    if (formData.classification === "" || !formData.classification) {
      errors.classification.addError("Classification cannot be blank");
    }
    if (formData.probability < 0 || formData.probability > 1) {
      errors.probability.addError(
        "Probability must be between 0 and 1, or blank",
      );
    }
    return errors;
  };

  return (
    <Form
      schema={formSchema}
      validator={validator}
      customValidate={validate}
      uiSchema={uiSchema}
      widgets={widgets}
      onSubmit={handleSubmit}
      disabled={submissionRequestInProcess}
      formData={selectedFormData}
      onChange={({ formData }) => {
        setSelectedFormData(formData);
      }}
    />
  );
};

ClassificationForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
  taxonomyList: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      created_at: PropTypes.string,
      isLatest: PropTypes.bool,
      version: PropTypes.string,
    }),
  ).isRequired,
};

export default ClassificationForm;
