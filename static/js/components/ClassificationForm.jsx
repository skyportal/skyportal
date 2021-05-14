import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import TextField from "@material-ui/core/TextField";
import MenuItem from "@material-ui/core/MenuItem";
import Select from "@material-ui/core/Select";
import Input from "@material-ui/core/Input";
import InputLabel from "@material-ui/core/InputLabel";
import Chip from "@material-ui/core/Chip";
import { makeStyles } from "@material-ui/core/styles";
import Form from "@rjsf/material-ui";

import { showNotification } from "baselayer/components/Notifications";
import * as Actions from "../ducks/source";

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

const ClassificationForm = ({ obj_id, taxonomyList }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);
  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);
  const groupIDToName = {};
  groups.forEach((g) => {
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

  const latestTaxonomyList = taxonomyList.filter((t) => t.isLatest);

  const handleSubmit = async ({ formData }) => {
    setSubmissionRequestInProcess(true);
    // Get the classification without the context
    const classification = formData.classification.split(" <> ")[0];
    const data = {
      taxonomy_id: parseInt(formData.taxonomy, 10),
      obj_id,
      classification,
      probability: formData.probability,
    };
    if (formData.groupIDs) {
      data.group_ids = formData.groupIDs.map((id) => parseInt(id, 10));
    }
    const result = await dispatch(Actions.addClassification(data));
    setSubmissionRequestInProcess(false);
    if (result.status === "success") {
      dispatch(showNotification("Classification saved"));
    }
  };

  // Custom form widget for the classifications to format and display the contexts as well
  const CustomClassificationWidget = ({ value, onChange, options }) => (
    <TextField
      id="classification"
      inputProps={{ MenuProps: { disableScrollLock: true } }}
      select
      required
      label="Classification"
      value={value || ""}
      onChange={(event) => {
        onChange(event.target.value);
      }}
    >
      {options.enumOptions.map((option) => {
        const [classification, context] = option.value.split(" <> ");
        return (
          <MenuItem key={option.value} value={option.value}>
            <span>
              <b>{classification}</b>
              &nbsp;
              {context !== "" && <br />}
              {context}
            </span>
          </MenuItem>
        );
      })}
    </TextField>
  );

  CustomClassificationWidget.propTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
    options: PropTypes.shape({
      enumOptions: PropTypes.arrayOf(PropTypes.shape({})),
    }).isRequired,
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
        MenuProps: { disableScrollLock: true },
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
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
  };

  const CustomGroupsWidget = ({ value, onChange, options }) => (
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
            {selected.map((group) => (
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
          options.enumOptions.map((group) => (
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

  CustomGroupsWidget.propTypes = {
    value: PropTypes.arrayOf(PropTypes.string).isRequired,
    onChange: PropTypes.func.isRequired,
    options: PropTypes.shape({
      enumOptions: PropTypes.arrayOf(PropTypes.shape({})),
    }).isRequired,
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
          enum: groups.map((group) => group.id.toString()),
          enumNames: groups.map((group) => group.name),
        },
        uniqueItems: true,
      },
      taxonomy: {
        type: "string",
        title: "Taxonomy",
        enum: latestTaxonomyList.map((taxonomy) => taxonomy.id.toString()),
        enumNames: latestTaxonomyList.map(
          (taxonomy) => `${taxonomy.name} (${taxonomy.version})`
        ),
      },
    },
    dependencies: {
      taxonomy: {
        oneOf: [],
      },
    },
  };
  latestTaxonomyList.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy).map(
      (option) =>
        `${option.class} <> ${
          option.context.length > 0 ? option.context.join(" « ") : ""
        }`
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
      },
    });
  });
  const uiSchema = {
    groupIDs: { "ui:widget": "customGroupsWidget" },
    classification: { "ui:widget": "customClassificationWidget" },
    probability: { "ui:widget": "customProbabilityWidget" },
  };

  return (
    <Form
      schema={formSchema}
      uiSchema={uiSchema}
      widgets={widgets}
      onSubmit={handleSubmit}
      disabled={submissionRequestInProcess}
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
    })
  ).isRequired,
};

export default ClassificationForm;
