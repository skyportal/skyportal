import React, { useState } from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";
import { makeStyles } from "tss-react/mui";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

const useStyles = makeStyles()(() => ({
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    maxWidth: "100%",
    "& > *": {
      maxWidth: "inherit",
    },
  },
}));

const SourcesList = ({ sources }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };

  // reorder the sources list alphabetically descending
  sources.sort((a, b) => (a > b ? 1 : -1));

  return (
    <div>
      <Button
        size="small"
        id="basic-button"
        aria-controls={open ? "basic-menu" : undefined}
        aria-haspopup="true"
        aria-expanded={open ? "true" : undefined}
        onClick={handleClick}
      >
        Added {sources.length} sources
      </Button>
      <Menu
        id="basic-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          "aria-labelledby": "basic-button",
        }}
      >
        {sources.map((source) => (
          <MenuItem key={source}>
            <Link
              to={`/source/${source}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {source}
            </Link>
          </MenuItem>
        ))}
      </Menu>
    </div>
  );
};

SourcesList.propTypes = {
  sources: PropTypes.arrayOf(PropTypes.string).isRequired,
};

const CatalogQueryLists = ({ catalog_queries }) => {
  const { classes } = useStyles();

  if (!catalog_queries || catalog_queries.length === 0) {
    return <p>No catalog queries for this event.</p>;
  }

  const renderStatus = (params) => {
    const query = params.row;
    let text = <div>{query?.status}</div>;
    if (query?.status?.includes("completed: Added ")) {
      let transients = query?.status?.split("completed: Added ")[1];
      // split by commas
      transients = transients.split(",");
      text = <SourcesList sources={transients} />;
    }
    return text;
  };

  const renderPayload = (params) => (
    <div>{JSON.stringify(params.row.payload)}</div>
  );

  const columns = [
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: renderStatus,
    },
    {
      field: "ntransients",
      headerName: "Payload",
      flex: 1,
      minWidth: 200,
      sortable: false,
      renderCell: renderPayload,
    },
  ];

  return (
    <div className={classes.container}>
      <StyledDataGrid
        autoHeight
        rows={catalog_queries}
        columns={columns}
        getRowId={(row) => row.id}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        pageSizeOptions={[1, 10, 15]}
        showToolbar
        sx={{ width: "100%" }}
      />
    </div>
  );
};

CatalogQueryLists.propTypes = {
  catalog_queries: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      payload: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      status: PropTypes.string,
    }),
  ).isRequired,
};

export default CatalogQueryLists;
