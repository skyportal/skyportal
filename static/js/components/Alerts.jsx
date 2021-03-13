import React from "react";
import { useHistory } from "react-router-dom";

import Typography from "@material-ui/core/Typography";
import Card from "@material-ui/core/Card";
import CardActions from "@material-ui/core/CardActions";
import CardContent from "@material-ui/core/CardContent";

import TextField from "@material-ui/core/TextField";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import FormHelperText from "@material-ui/core/FormHelperText";
import FormControl from "@material-ui/core/FormControl";
import Select from "@material-ui/core/Select";

import Grid from "@material-ui/core/Grid";

import Button from "@material-ui/core/Button";
import { makeStyles } from "@material-ui/core/styles";
import { useForm, Controller } from "react-hook-form";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    "& > *": {
      margin: theme.spacing(1),
    },
  },
  whitish: {
    color: "#f0f0f0",
  },
  visuallyHidden: {
    border: 0,
    clip: "rect(0 0 0 0)",
    height: 1,
    margin: -1,
    overflow: "hidden",
    padding: 0,
    position: "absolute",
    top: 20,
    width: 1,
  },
  search_button: {
    color: "#f0f0f0 !important",
  },
  margin_bottom: {
    "margin-bottom": "2em",
  },
  margin_left: {
    "margin-left": "2em",
  },
  image: {
    padding: theme.spacing(1),
    textAlign: "center",
    color: theme.palette.text.secondary,
  },
  paper: {
    padding: theme.spacing(2),
    textAlign: "center",
    color: theme.palette.text.secondary,
  },
  formControl: {
    width: "100%",
  },
  selectEmpty: {
    width: "100%",
  },
  header: {
    paddingBottom: "0.625rem",
  },
}));

const Alerts = () => {
  const classes = useStyles();

  const history = useHistory();

  const { register, handleSubmit, control } = useForm();

  const submitForm = (data) => {
    const path = `/alerts/${data.instrument}/${data.object_id.trim()}`;
    history.push(path);
  };

  return (
    <div>
      <Typography variant="h6" className={classes.header}>
        Search objects from alert streams
      </Typography>

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Card className={classes.root}>
            <form onSubmit={handleSubmit(submitForm)}>
              <CardContent>
                <FormControl required className={classes.selectEmpty}>
                  <InputLabel name="alert-stream-select-required-label">
                    Instrument
                  </InputLabel>
                  <Controller
                    labelId="alert-stream-select-required-label"
                    name="instrument"
                    as={Select}
                    defaultValue="ztf"
                    control={control}
                    rules={{ required: true }}
                  >
                    <MenuItem value="ztf">ZTF</MenuItem>
                  </Controller>
                  <FormHelperText>Required</FormHelperText>
                </FormControl>

                <TextField
                  autoFocus
                  required
                  margin="dense"
                  name="object_id"
                  label="objectId"
                  type="text"
                  fullWidth
                  inputRef={register({ required: true, minLength: 3 })}
                />
              </CardContent>
              <CardActions>
                <Button
                  type="submit"
                  variant="contained"
                  color="primary"
                  className={classes.button_add}
                >
                  Search
                </Button>
              </CardActions>
            </form>
          </Card>
        </Grid>
      </Grid>
    </div>
  );
};

export default Alerts;
