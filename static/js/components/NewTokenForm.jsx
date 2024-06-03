import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";

import TextField from "@mui/material/TextField";
import Checkbox from "@mui/material/Checkbox";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import FormControlLabel from "@mui/material/FormControlLabel";

/* For group selection:
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
*/
import { Controller, useForm } from "react-hook-form";
import Button from "./Button";

import * as ProfileActions from "../ducks/profile";

// const NewTokenForm = ({ acls, groups }) => {
const NewTokenForm = ({ availableAcls }) => {
  const dispatch = useDispatch();

  const {
    handleSubmit,
    register,
    reset,
    control,

    formState: { errors },
  } = useForm();

  useEffect(() => {
    reset({
      acls: Array(availableAcls.length).fill(false),
    });
  }, [reset, availableAcls]);

  const onSubmit = async (data) => {
    const selectedACLs = availableAcls?.filter(
      (include, idx) => data.acls[idx],
    );
    data.acls = selectedACLs;

    // Token groups are not currently supported
    /*
    if (data.group === 'All') {
      delete data.group;
    }
    */

    const result = await dispatch(ProfileActions.createToken(data));
    if (result.status === "success") {
      reset();
    }
  };

  return (
    <div>
      <Typography variant="h5">
        Generate New Token for Command-Line Authentication
      </Typography>

      <Card>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            <Box>
              <TextField
                label="Token name"
                {...register("name", { required: true })}
                name="name"
                error={!!errors.name}
                helperText={errors.name ? "Required" : ""}
              />
            </Box>
            <Box>
              <Box component="span" mr={1} fontWeight="bold">
                ACLs:
              </Box>
              {availableAcls?.map((acl, idx) => (
                <FormControlLabel
                  key={acl}
                  control={
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <Checkbox
                          onChange={(event) => onChange(event.target.checked)}
                          checked={value}
                          data-testid={`acls[${idx}]`}
                        />
                      )}
                      name={`acls[${idx}]`}
                      control={control}
                      defaultValue={false}
                    />
                  }
                  label={acl}
                />
              ))}
            </Box>
            {/*
            For when we start to support group selection
            Select Token Group:
            <Controller
              as={(
                <Select>
                  <MenuItem value="All" key="0">
                    All
                  </MenuItem>
                  {groups.map((group) => (
                    <MenuItem value={group.id} key={group.id}>
                      {group.name}
                    </MenuItem>
                  ))}
                </Select>
              )}
              name="group"
              control={control}
              defaultValue="All"
            /> */}
            <Button secondary type="submit">
              Generate Token
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
NewTokenForm.propTypes = {
  availableAcls: PropTypes.arrayOf(PropTypes.string).isRequired,
  //  groups: PropTypes.arrayOf(PropTypes.object).isRequired
};

export default NewTokenForm;
