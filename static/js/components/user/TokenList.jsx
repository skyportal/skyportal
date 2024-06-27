import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";

import makeStyles from "@mui/styles/makeStyles";

import MUIDataTable from "mui-datatables";
import Button from "../Button";
import UpdateTokenACLs from "./UpdateTokenACLs";
import SharePage from "../SharePage";

import * as Action from "../../ducks/profile";

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

  const profile = useSelector((state) => state.profile);

  if (!tokens) {
    return <div />;
  }

  const deleteToken = (token_id) => {
    dispatch(Action.deleteToken(token_id));
  };

  const renderValue = (value) => (
    <div>
      <TextField id={value} value={value} readOnly={1} />
      <Button secondary size="small" onClick={() => copyToken(value)}>
        Copy to Clipboard
      </Button>
    </div>
  );

  const renderQRCode = (dataIndex) => {
    const tokenId = tokens[dataIndex].id;
    return (
      <div>
        <SharePage value={tokenId} />
      </div>
    );
  };

  const renderACLs = (dataIndex) => {
    const tokenId = tokens[dataIndex].id;
    const tokenACLs = tokens[dataIndex].acls;
    return (
      <div>
        {tokens[dataIndex].acls.join(", ")}
        <div className={classes.sourceInfo}>
          <UpdateTokenACLs
            tokenId={tokenId}
            currentACLs={tokenACLs}
            availableACLs={profile.permissions}
          />
        </div>
      </div>
    );
  };

  const renderDelete = (dataIndex) => {
    const tokenId = tokens[dataIndex].id;
    return (
      <Button secondary size="small" onClick={() => deleteToken(tokenId)}>
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
    {
      name: "qr",
      label: "QR Code",
      options: {
        customBodyRenderLite: renderQRCode,
      },
    },
    { name: "name", label: "Name" },
    {
      name: "acls",
      label: "ACLs",
      options: {
        customBodyRenderLite: renderACLs,
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
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable data={tokens} options={options} columns={columns} />
          </ThemeProvider>
        </StyledEngineProvider>
      </Paper>
    </div>
  );
};
TokenList.propTypes = {
  tokens: PropTypes.arrayOf(PropTypes.object).isRequired, // eslint-disable-line react/forbid-prop-types
};

export default TokenList;
