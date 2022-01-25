import React, { useState } from "react";

import { useSelector } from "react-redux";
import Typography from "@material-ui/core/Typography";
import {
    makeStyles,
    createMuiTheme,
    MuiThemeProvider,
    useTheme,
  } from "@material-ui/core/styles";
import MUIDataTable from "mui-datatables";

const useStyles = makeStyles((theme) => ({
    container: {
      width: "100%",
      overflow: "scroll",
    },
    eventTags: {
      marginLeft: "0.5rem",
      "& > div": {
        margin: "0.25rem",
        color: "white",
        background: theme.palette.primary.main,
      },
    },
  }));
  
  // Tweak responsive styling
  const getMuiTheme = (theme) =>
    createMuiTheme({
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

const ListOfShifts = () => {
    const classes = useStyles();
    const theme = useTheme();
    //const shifts = useSelector((state) => state.shifts);
    var shifts = [];
    shifts = useSelector((state) => state.shifts.all);
    const current_time = new Date().toLocaleString();
    // shifts = require("./myshifts.json");
    
    const columns = [
        {
          name: "name",
          label: "Name",
          options: {
          },
        },
        {
          name: "start",
          label: "Start",
          options: {
          },
        },
        {
          name: "end",
          label: "End",
          options: {

          },
        },
        {
          name: "comments",
          label: "Comments",
          options: {
          },
        },
        {
          name: "other_shifters",
          label: "Other Shifters",
          options: {
            },
        },
    ];

    const options = {
    search: true,
    selectableRows: "none",
    elevation: 0,
    };
return (
    <div>
    <Typography variant="h5">List of Shifts</Typography>
        <MuiThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              data={shifts}
              options={options}
              columns={columns}
            />
        </MuiThemeProvider>
    </div>
  );
};

export default ListOfShifts;
