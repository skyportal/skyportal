import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";

import TextField from "@material-ui/core/TextField";
import Checkbox from "@material-ui/core/Checkbox";
import Button from "@material-ui/core/Button";
import Card from "@material-ui/core/Card";
import CardContent from "@material-ui/core/CardContent";
import Box from "@material-ui/core/Box";
import Typography from "@material-ui/core/Typography";
import FormControlLabel from "@material-ui/core/FormControlLabel";

/* For group selection:
import Select from '@material-ui/core/Select';
import MenuItem from '@material-ui/core/MenuItem';
*/

import { useForm, Controller } from "react-hook-form";

import * as ProfileActions from "../ducks/profile";

// const NewTokenForm = ({ acls, groups }) => {
const NewTokenForm = ({ acls }) => {
  const dispatch = useDispatch();

  const { handleSubmit, register, errors, reset, control } = useForm();

  useEffect(() => {
    reset({
      acls: Array(acls.length).fill(false),
    });
  }, [reset, acls]);

  const onSubmit = async (data) => {
    const selectedACLs = acls.filter((include, idx) => data.acls[idx]);
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
                inputRef={register({ required: true })}
                name="name"
                error={!!errors.name}
                helperText={errors.name ? "Required" : ""}
              />
            </Box>
            <Box>
              <Box component="span" mr={1} fontWeight="bold">
                ACLs:
              </Box>
              {acls.map((acl, idx) => (
                <FormControlLabel
                  key={acl}
                  control={
                    <Controller
                      as={Checkbox}
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
            <Button variant="contained" type="submit">
              Generate Token
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
NewTokenForm.propTypes = {
  acls: PropTypes.arrayOf(PropTypes.string).isRequired,
  //  groups: PropTypes.arrayOf(PropTypes.object).isRequired
};

export default NewTokenForm;
