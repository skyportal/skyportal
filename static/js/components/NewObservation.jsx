// NewObservation.jsx
import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dataUriToBuffer from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { fetchObservations, uploadObservations } from "../ducks/observations";
import NewDropDownSearchBar from "./NewDropDownSearchBar";

const NewObservation = () => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const dispatch = useDispatch();

  // State variables for selected instrument and search input
  const [selectedInstrument, setSelectedInstrument] = useState(null);
  const [searchValue, setSearchValue] = useState("");

  // Event handler for changes in the selected instrument
  const handleInstrumentChange = (event, newValue) => {
    setSelectedInstrument(newValue);
  };

  // Event handler for changes in the search input
  const handleSearchChange = (value) => {
    setSearchValue(value);
  };

  // Event handler for form submission
  const handleSubmit = async ({ formData }) => {
    // Convert data URI to ASCII
    const ascii = dataUriToBuffer(formData.file).toString();
    // Prepare payload for observation upload
    const payload = {
      observationData: ascii,
      instrumentID: selectedInstrument ? selectedInstrument.id : null,
    };
    // Dispatch the observation upload action
    const result = await dispatch(uploadObservations(payload));
    // Display a notification if the observation upload is successful
    if (result.status === "success") {
      dispatch(showNotification("Observation saved"));
      dispatch(fetchObservations());
    }
  };

  // JSON schema for the observation form
  const observationFormSchema = {
    type: "object",
    properties: {
      file: {
        type: "string",
        format: "data-url",
        title: "Observation file",
        description: "Observation file",
      },
    },
    required: ["file"],
  };

  // Render the observation form with the NewDropDownSearchBar component
  return (
    <Form
      schema={observationFormSchema}
      validator={validator}
      onSubmit={handleSubmit}
    >
      <NewDropDownSearchBar
        optionsList={instrumentList}
        selectedOption={selectedInstrument}
        onOptionChange={handleInstrumentChange}
        searchValue={searchValue}
        onSearchChange={handleSearchChange}
        label="Select an instrument"
      />
    </Form>
  );
};

export default NewObservation;
