import React from "react";
import { useSelector } from "react-redux";
import Typography from "@material-ui/core/Typography";
import { Link } from "react-router-dom";
import {
    makeStyles,
    createMuiTheme,
    MuiThemeProvider,
    useTheme,
  } from "@material-ui/core/styles";
import MUIDataTable from "mui-datatables";


import UserProfileInfo from "./UserProfileInfo";

const useStyles = makeStyles((theme) => ({
    avatar: {
      padding: `${theme.spacing(2)}px 0 ${theme.spacing(1)}px 0`,
    },
    nodecor: {
      textDecoration: "none",
      textAlign: "center",
      color: theme.palette.text.primary,
    },
    centerContent: {
      justifyContent: "center",
    },
    signOutMargin: {
      margin: `0 0 ${theme.spacing(2)}px 0`,
    },
    typography: {
      padding: theme.spacing(1),
    },
    invisible: {
      display: "none",
    },
    paddingSides: {
      margin: `0 ${theme.spacing(2)}px 0 ${theme.spacing(2)}px`,
    },
    popoverMenu: {
      minWidth: "10rem",
      maxWidth: "20rem",
    },
  }));

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
const MyShifts = () => {
  const profile = useSelector((state) => state.profile);
  const groups = useSelector((state) => state.groups.user);
  const classes = useStyles();
  const theme = useTheme();
  const columns = [
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
    const shifts = [];

  return (
    <div>
        <Typography variant="h5">Your next shifts</Typography>
            <MuiThemeProvider theme={getMuiTheme(theme)}>
                <MUIDataTable
                data={shifts}
                options={options}
                columns={columns}
                />
            </MuiThemeProvider>
      <div>

      </div>
      &nbsp;
      <br />
      <div>
        <Link
            to="/list_shifts"
            role="link"
            className={classes.nodecor}
        >
            <p className={classes.centerContent}>See all shifts here</p>
        </Link>
      </div>
      &nbsp;
    </div>
  );
};

export default MyShifts;
