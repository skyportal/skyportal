import React, { useState } from "react";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Input from "@mui/material/Input";
import InputLabel from "@mui/material/InputLabel";
import Chip from "@mui/material/Chip";
import { makeStyles } from "tss-react/mui";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as Actions from "../../ducks/source";

const useStyles = makeStyles()(() => ({
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
const addNodePaths = (
  nodePaths: any[],
  hierarchy: any,
  prefix_path: any[] = [],
) => {
  const thisNodePath = [...prefix_path];

  if (
    hierarchy.class !== undefined &&
    hierarchy.class !== "Time-domain Source"
  ) {
    thisNodePath.push(hierarchy.class);
    nodePaths.push(thisNodePath);
  }

  hierarchy.subclasses?.forEach((item: any) => {
    if (typeof item === "object") {
      addNodePaths(nodePaths, item, thisNodePath);
    }
  });
};

// For each class in the hierarchy, return its name
// as well as the path from the root of hierarchy to that class
export const allowedClasses = (hierarchy: any) => {
  const classPaths: any[] = [];
  addNodePaths(classPaths, hierarchy);

  const classes = classPaths.map((path) => ({
    class: path.pop(),
    context: path.reverse(),
  }));

  return classes;
};

interface CustomProbabilityWidgetProps {
  value?: string;
  onChange: (...a: any[]) => void;
}

// Custom form widget for probability because rxjs MUI UpdownWidget does not have working min/max/step
// https://github.com/rjsf-team/react-jsonschema-form/issues/2022
const CustomProbabilityWidget = ({
  value = "",
  onChange,
}: CustomProbabilityWidgetProps) => (
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

interface CustomGroupsWidgetProps {
  value: string[];
  onChange: (...a: any[]) => void;
  options: { enumOptions?: any[] };
}

const CustomGroupsWidget = ({
  value,
  onChange,
  options,
}: CustomGroupsWidgetProps) => {
  const { classes } = useStyles();
  const groups = useAppSelector((state) => state.groups.userAccessible);

  const groupIDToName: Record<string, any> = {};
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
        Choose Group (public if not specified)
      </InputLabel>
      <Select
        id="groupSelect"
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        input={<Input id="selectGroupsChip" />}
        labelId="classificationGroupSelectLabel"
        value={(value || "") as any}
        renderValue={(selected: any) => (
          <div className={classes.chips}>
            {selected?.map((group: any) => (
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
        {(options.enumOptions?.length ?? 0) > 0 &&
          options.enumOptions?.map((group: any) => (
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

interface CustomClassificationWidgetProps {
  value?: string;
  onChange: (...a: any[]) => void;
  options: { enumOptions?: any[] };
}

// Custom form widget for the classifications to format and display the contexts as well
const CustomClassificationWidget = ({
  value = "",
  onChange,
  options,
}: CustomClassificationWidgetProps) => {
  const filteringOptions = createFilterOptions<any>({
    matchFrom: "start",
    stringify: (option) => option,
  });
  return (
    <Autocomplete
      id="classification"
      filterOptions={filteringOptions}
      options={options.enumOptions?.map((option: any) => option.value) ?? []}
      onChange={(event, newValue) => {
        onChange(newValue);
      }}
      value={value || ""}
      renderOption={(props: any, option: any) => {
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

interface ClassificationFormProps {
  obj_id: string;
  taxonomyList: any[];
}

const ClassificationForm = ({
  obj_id,
  taxonomyList,
}: ClassificationFormProps) => {
  const dispatch = useAppDispatch();
  const groups = useAppSelector((state) => state.groups.userAccessible);
  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);

  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);
  const [selectedFormData, setSelectedFormData] = useState<any>({});

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setSubmissionRequestInProcess(true);
    // Get the classification without the context
    const classification = formData.classification.split(" <> ")[0];
    const data: any = {
      taxonomy_id: parseInt(formData.taxonomy, 10),
      obj_id,
      classification,
      probability: formData.probability,
      ml: formData.ml || false,
    };
    if (formData.groupIDs) {
      data.group_ids = formData.groupIDs?.map((id: any) => parseInt(id, 10));
    }
    const result: any = await dispatch(Actions.addClassification(data));
    setSubmissionRequestInProcess(false);
    if (result.status === "success") {
      dispatch(showNotification("Classification saved"));
    }
  };

  const widgets = {
    customClassificationWidget: CustomClassificationWidget,
    customProbabilityWidget: CustomProbabilityWidget,
    customGroupsWidget: CustomGroupsWidget,
  };

  const formSchema: any = {
    description: "Add Classification",
    type: "object",
    required: ["taxonomy", "classification", "probability"],
    properties: {
      groupIDs: {
        type: "array",
        items: {
          type: "string",
          enum: groups?.map((group) => group.id.toString()),
        },
        uniqueItems: true,
      },
      taxonomy: {
        type: "string",
        title: "Taxonomy",
        enum: latestTaxonomyList?.map((taxonomy) => taxonomy.id.toString()),
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
  const uiSchema: any = {
    groupIDs: {
      "ui:widget": "customGroupsWidget",
      "ui:enumNames": groups?.map((group) => group.name),
    },
    taxonomy: {
      "ui:enumNames": latestTaxonomyList?.map(
        (taxonomy) => `${taxonomy.name} (${taxonomy.version})`,
      ),
    },
    classification: { "ui:widget": "customClassificationWidget" },
    probability: { "ui:widget": "customProbabilityWidget" },
  };

  const validate = (formData: any, errors: any) => {
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
      widgets={widgets as any}
      onSubmit={handleSubmit as any}
      disabled={submissionRequestInProcess}
      formData={selectedFormData}
      onChange={
        (({ formData }: { formData: any }) => {
          setSelectedFormData(formData);
        }) as any
      }
    />
  );
};

export default ClassificationForm;
