import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";

import { makeStyles } from "tss-react/mui";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import UpdateTokenACLs from "./UpdateTokenACLs";
import SharePage from "../SharePage";

import * as Action from "../../ducks/profile";

const useStyles = makeStyles()(() => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
}));

const copyToken = (elementID) => {
  const el = document.getElementById(elementID);
  el.select();
  document.execCommand("copy");
};

const TokenList = ({ tokens }) => {
  const { classes } = useStyles();
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

  const renderQRCode = (params) => (
    <div>
      <SharePage value={params.row.id} />
    </div>
  );

  const renderACLs = (params) => {
    const tokenId = params.row.id;
    const tokenACLs = params.row.acls;
    return (
      <div>
        {(params.row.acls || []).join(", ")}
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

  const renderDelete = (params) => (
    <Button secondary size="small" onClick={() => deleteToken(params.row.id)}>
      Delete
    </Button>
  );

  const columns = [
    {
      field: "id",
      headerName: "Value",
      flex: 1,
      minWidth: 200,
      sortable: false,
      renderCell: (params) => renderValue(params.value),
    },
    {
      field: "qr",
      headerName: "QR Code",
      width: 120,
      sortable: false,
      renderCell: renderQRCode,
    },
    { field: "name", headerName: "Name", flex: 1, minWidth: 120 },
    {
      field: "acls",
      headerName: "ACLs",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: renderACLs,
    },
    { field: "created_at", headerName: "Created", flex: 1, minWidth: 160 },
    {
      field: "delete",
      headerName: "Delete",
      width: 110,
      sortable: false,
      renderCell: renderDelete,
    },
  ];

  return (
    <div>
      <Typography variant="h5">My Tokens</Typography>
      <Paper className={classes.container}>
        <StyledDataGrid
          autoHeight
          rows={tokens}
          columns={columns}
          getRowId={(row) => row.id}
          showToolbar
        />
      </Paper>
    </div>
  );
};
TokenList.propTypes = {
  tokens: PropTypes.arrayOf(PropTypes.object).isRequired, // eslint-disable-line react/forbid-prop-types
};

export default TokenList;
