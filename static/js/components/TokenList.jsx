import React from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";

import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import {
  makeStyles,
  createTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";

import MUIDataTable from "mui-datatables";

import * as Action from "../ducks/profile";

const useStyles = makeStyles(() => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    overrides: {
      MUIDataTablePagination: {
        toolbar: {
          flexFlow: "row wrap",
          justifyContent: "flex-end",
          padding: "0.5rem 1rem 0",
          [theme.breakpoints.up("sm")]: {
            // Cancel out small screen styling and replace
            padding: "0px",
            paddingRight: "2px",
            flexFlow: "row nowrap",
          },
        },
        tableCellContainer: {
          padding: "1rem",
        },
        selectRoot: {
          marginRight: "0.5rem",
          [theme.breakpoints.up("sm")]: {
            marginLeft: "0",
            marginRight: "2rem",
          },
        },
      },
    },
  });

const copyToken = (elementID) => {
  const el = document.getElementById(elementID);
  el.select();
  document.execCommand("copy");
};

const TokenList = ({ tokens }) => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();
  if (!tokens) {
    return <div />;
  }

  const deleteToken = (token_id) => {
    dispatch(Action.deleteToken(token_id));
  };

  const renderValue = (value) => (
    <div>
      <TextField id={value} value={value} readOnly={1} />
      <Button variant="contained" size="small" onClick={() => copyToken(value)}>
        Copy to Clipboard
      </Button>
    </div>
  );

  const renderACLs = (value) => value.join(", ");

  const renderDelete = (dataIndex) => {
    const tokenId = tokens[dataIndex].id;
    return (
      <Button
        variant="contained"
        size="small"
        onClick={() => deleteToken(tokenId)}
      >
        Delete
      </Button>
    );
  };

  const columns = [
    {
      name: "id",
      label: "Value",
      options: {
        customBodyRender: renderValue,
      },
    },
    { name: "name", label: "Name" },
    {
      name: "acls",
      label: "ACLs",
      options: {
        customBodyRender: renderACLs,
      },
    },
    { name: "created_at", label: "Created" },
    {
      name: "delete",
      label: "Delete",
      options: {
        customBodyRenderLite: renderDelete,
      },
    },
  ];

  const options = {
    filter: false,
    sort: false,
    print: true,
    download: true,
    search: true,
    selectableRows: "none",
    elevation: 0,
  };

  return (
    <div>
      <Typography variant="h5">My Tokens</Typography>
      <Paper className={classes.container}>
        <MuiThemeProvider theme={getMuiTheme(theme)}>
          <MUIDataTable data={tokens} options={options} columns={columns} />
        </MuiThemeProvider>
      </Paper>
    </div>
  );
};
TokenList.propTypes = {
  tokens: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export default TokenList;
