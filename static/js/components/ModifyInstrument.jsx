import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Form from "@rjsf/material-ui";
import CircularProgress from "@material-ui/core/CircularProgress";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import { makeStyles } from "@material-ui/core/styles";
import dataUriToBuffer from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { modifyInstrument } from "../ducks/instrument";
import { fetchInstruments } from "../ducks/instruments";
// eslint-disable-next-line import/no-cycle
import { instrumentTitle, instrumentInfo } from "./InstrumentPage";

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
  allocationSelectItem: {
    whiteSpace: "break-spaces",
  },
  localizationSelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

const ModifyInstrument = () => {
  const classes = useStyles();
  const textClasses = textStyles();

  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { enum_types } = useSelector((state) => state.enum_types);
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    if (Object.keys(formData).includes("api_classname")) {
      // eslint-disable-next-line prefer-destructuring
      formData.api_classname = formData.api_classname[0];
    }
    if (Object.keys(formData).includes("api_classname_obsplan")) {
      // eslint-disable-next-line prefer-destructuring
      formData.api_classname_obsplan = formData.api_classname_obsplan[0];
    }
    if (Object.keys(formData).includes("field_data")) {
      formData.field_data = dataUriToBuffer(formData.field_data).toString();
    }
    if (Object.keys(formData).includes("field_region")) {
      formData.field_region = dataUriToBuffer(formData.field_region).toString();
    }
    const result = await dispatch(
      modifyInstrument(selectedInstrumentId, formData)
    );
    if (result.status === "success") {
      dispatch(showNotification("Instrument saved"));
      dispatch(fetchInstruments());
    }
  };

  useEffect(() => {
    const getInstruments = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(fetchInstruments());

      const { data } = result;
      setSelectedInstrumentId(data[0]?.id);
    };

    getInstruments();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedInstrumentId]);

  if (instrumentList.length === 0 || telescopeList.length === 0) {
    return <h3>No instruments available...</h3>;
  }

  if (enum_types.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  // need to check both of these conditions as selectedAllocationId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if allocationList is not
  // empty.
  if (!selectedInstrumentId) {
    return <h3>No instruments available...</h3>;
  }

  const api_classnames = [...enum_types.ALLOWED_API_CLASSNAMES];
  api_classnames.push("");
  const filters = [...enum_types.ALLOWED_BANDPASSES];

  if (telescopeList.length === 0 || instrumentList.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSelectedInstrumentChange = (e) => {
    setSelectedInstrumentId(e.target.value);
  };

  function validate(formData, errors) {
    const oldFilters = [];
    instLookUp[selectedInstrumentId].filters?.forEach((filter) => {
      oldFilters.push(filter);
    });
    const oldFiltersUnique = [...new Set(oldFilters)];

    const newFilters = [];
    formData.filters?.forEach((filter) => {
      newFilters.push(filter);
    });
    const newFiltersUnique = [...new Set(newFilters)];

    const result = oldFiltersUnique.every((val) =>
      newFiltersUnique.includes(val)
    );
    if (errors && formData.filters && !result) {
      errors.filters.addError("New filter list must contain old filter list.");
    }
    if (errors && formData.api_classname && formData.api_classname.length > 1) {
      errors.api_classname.addError("Must only choose one API class.");
    }
    if (
      errors &&
      formData.api_classname_obsplan &&
      formData.api_classname_obsplan.length > 1
    ) {
      errors.api_classname_obsplan.addError("Must only choose one API class.");
    }
    return errors;
  }

  const instrumentFormSchema = {
    type: "object",
    properties: {
      filters: {
        type: "array",
        items: {
          type: "string",
          enum: filters,
        },
        uniqueItems: true,
        title: "Filter list",
      },
      api_classname: {
        type: "array",
        items: {
          type: "string",
          enum: api_classnames,
        },
        uniqueItems: true,
        title: "API Classname",
      },
      api_classname_obsplan: {
        type: "array",
        items: {
          type: "string",
          enum: api_classnames,
        },
        uniqueItems: true,
        title: "API Observation Plan Classname",
      },
      field_data: {
        type: "string",
        format: "data-url",
        title: "Field data file",
        description: "Field data file",
      },
      field_region: {
        type: "string",
        format: "data-url",
        title: "Field region file",
        description: "Field region file",
      },
    },
  };

  return (
    <div className={classes.container}>
      <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="instrumentSelectLabel"
        value={selectedInstrumentId}
        onChange={handleSelectedInstrumentChange}
        name="modifyInstrumentSelect"
        className={classes.instrumentSelect}
      >
        {instrumentList?.map((instrument) => (
          <MenuItem
            value={instrument.id}
            key={instrument.id}
            className={classes.instrumentSelectItem}
          >
            {`${telLookUp[instrument.telescope_id].name}
             / ${instrument.name}`}
          </MenuItem>
        ))}
      </Select>
      <List component="nav">
        <ListItem button key={selectedInstrumentId}>
          <ListItemText
            primary={instrumentTitle(
              instLookUp[selectedInstrumentId],
              telescopeList
            )}
            secondary={instrumentInfo(
              instLookUp[selectedInstrumentId],
              telescopeList
            )}
            classes={textClasses}
          />
        </ListItem>
      </List>
      <Form
        schema={instrumentFormSchema}
        onSubmit={handleSubmit}
        // eslint-disable-next-line react/jsx-no-bind
        validate={validate}
        liveValidate
      />
    </div>
  );
};

export default ModifyInstrument;
