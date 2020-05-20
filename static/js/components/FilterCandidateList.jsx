import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Checkbox from "@material-ui/core/Checkbox";
import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";
import { KeyboardDatePicker } from "@material-ui/pickers";
import { useForm, Controller } from "react-hook-form";

import * as candidatesActions from "../ducks/candidates";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";
import FormValidationError from "./FormValidationError";


const FilterCandidateList = ({ userGroups }) => {
  const { pageNumber, lastPage, totalMatches, numberingStart,
    numberingEnd } = useSelector((state) => state.candidates);

  const [jumpToPageInputValue, setJumpToPageInputValue] = useState("");

  const { handleSubmit, getValues, control, errors, reset } = useForm();

  useEffect(() => {
    reset({
      groupIDs: Array(userGroups.length).fill(true),
      startDate: null,
      endDate: null
    });
  }, [reset, userGroups]);

  const dispatch = useDispatch();

  let formState = getValues({ nest: true });

  const validateGroups = () => {
    formState = getValues({ nest: true });
    return formState.groupIDs.filter((value) => Boolean(value)).length >= 1;
  };

  const validateDates = () => {
    formState = getValues({ nest: true });
    if (!!formState.startDate && !!formState.endDate) {
      return formState.startDate <= formState.endDate;
    }
    return true;
  };

  const onSubmit = (data) => {
    const groupIDs = userGroups.map((g) => g.id);
    const selectedGroupIDs = groupIDs.filter((ID, idx) => data.groupIDs[idx]);
    data.groupIDs = selectedGroupIDs;
    // Convert dates to ISO for parsing on back-end
    if (data.startDate) {
      data.startDate = data.startDate.toISOString();
    }
    if (data.endDate) {
      data.endDate = data.endDate.toISOString();
    }
    dispatch(candidatesActions.fetchCandidates(data));
  };

  const handleClickNextPage = () => {
    dispatch(candidatesActions.fetchCandidates({ pageNumber: pageNumber + 1 }));
  };

  const handleClickPreviousPage = () => {
    dispatch(candidatesActions.fetchCandidates({ pageNumber: pageNumber - 1 }));
  };

  const handleJumpToPageInputChange = (e) => {
    setJumpToPageInputValue(e.target.value);
  };

  const handleClickJumpToPage = () => {
    dispatch(candidatesActions.fetchCandidates({ pageNumber: jumpToPageInputValue }));
  };

  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div>
          {
            (errors.startDate || errors.endDate) &&
              <FormValidationError message="Invalid date range." />
          }
          <Controller
            as={(
              <KeyboardDatePicker
                format="YYYY-MM-DD"
                value={formState.startDate}
                emptyLabel="Start Date"
              />
            )}
            rules={{ validate: validateDates }}
            name="startDate"
            control={control}
          />
          <Controller
            as={(
              <KeyboardDatePicker
                format="YYYY-MM-DD"
                value={formState.endDate}
                emptyLabel="End Date"
              />
            )}
            rules={{ validate: validateDates }}
            name="endDate"
            control={control}
            onChange={([selected]) => selected}
          />
        </div>
        <div>
          <FormControlLabel
            control={(
              <Controller
                as={Checkbox}
                name="unsavedOnly"
                control={control}
                defaultValue={false}
              />
            )}
            label="Show only unsaved candidates"
          />
        </div>
        <div>
          <Responsive
            element={FoldBox}
            title="Program Selection"
            mobileProps={{ folded: true }}
          >
            {
              errors.groupIDs &&
                <FormValidationError message="Select at least one group." />
            }
            {
              userGroups.map((group, idx) => (
                <FormControlLabel
                  key={group.id}
                  control={(
                    <Controller
                      as={Checkbox}
                      name={`groupIDs[${idx}]`}
                      control={control}
                      rules={{ validate: validateGroups }}
                      defaultValue
                    />
                  )}
                  label={group.name}
                />
              ))
            }
          </Responsive>
        </div>
        <div>
          <Button
            variant="contained"
            type="submit"
          >
            Submit
          </Button>
        </div>
      </form>
      <div style={{ display: "inline-block" }}>
        <Button
          variant="contained"
          onClick={handleClickPreviousPage}
          disabled={pageNumber === 1}
        >
          Previous Page
        </Button>
      </div>
      <div style={{ display: "inline-block" }}>
        <i>
          Displaying&nbsp;
          {numberingStart}
          -
          {numberingEnd}
          &nbsp;
          of&nbsp;
          {totalMatches}
          &nbsp;
          candidates.
        </i>
      </div>
      <div style={{ display: "inline-block" }}>
        <Button
          variant="contained"
          onClick={handleClickNextPage}
          disabled={lastPage}
        >
          Next Page
        </Button>
      </div>
      <div>
        <TextField
          label="Jump to Page Number"
          type="number"
          onChange={handleJumpToPageInputChange}
          value={jumpToPageInputValue}
          name="jumpToPageInputField"
        />
        <Button
          variant="contained"
          onClick={handleClickJumpToPage}
        >
          Jump to Page
        </Button>
      </div>
      <br />
      <br />
    </div>
  );
};
FilterCandidateList.propTypes = {
  userGroups: PropTypes.arrayOf(PropTypes.object).isRequired
};

export default FilterCandidateList;
