import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
// import { showNotification } from "baselayer/components/Notifications";
import CircularProgress from "@mui/material/CircularProgress";
import MUIDataTable from "mui-datatables";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
} from "@mui/material/styles";
import NewRecurringAPI from "./NewRecurringAPI";

import * as recurringAPIsActions from "../ducks/recurring_apis";

const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTablePagination: {
        styleOverrides: {
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
    },
  });

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  paperContent: {
    padding: "1rem",
  },
  recurringAPIDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  recurringAPIDeleteDisabled: {
    opacity: 0,
  },
}));

// const textStyles = makeStyles(() => ({
//   primary: {
//     fontWeight: "bold",
//     fontSize: "110%",
//   },
// }));

export function recurringAPITitle(recurringAPI) {
  if (!recurringAPI?.endpoint) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${recurringAPI?.endpoint} / ${recurringAPI?.method}`;

  return result;
}

export function recurringAPIInfo(recurringAPI) {
  if (!recurringAPI?.next_call) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `Next call: ${recurringAPI.next_call} / Delay [days]: ${recurringAPI.call_delay} / Active: ${recurringAPI.active}`;

  return result;
}

const RecurringAPIList = ({ recurringAPIs }) => {
  // const dispatch = useDispatch();
  const classes = useStyles();
  const theme = useTheme();
  // const [recurringAPIToDelete, setRecurringAPIToDelete] = useState(null);

  // const textClasses = textStyles();
  // const groups = useSelector((state) => state.groups.all);
  // const [dialogOpen, setDialogOpen] = useState(false);
  // const openDialog = (id) => {
  //   setDialogOpen(true);
  //   setRecurringAPIToDelete(id);
  // };
  // const closeDialog = () => {
  //   setDialogOpen(false);
  //   setRecurringAPIToDelete(null);
  // };

  // const renderDelete = () => {
  //   dispatch(
  //     recurringAPIsActions.deleteRecurringAPI(recurringAPIToDelete),
  //   ).then((result) => {
  //     if (result.status === "success") {
  //       dispatch(showNotification("RecurringAPI deleted"));
  //       closeDialog();
  //     }
  //   });
  // };

  const columns = [
    {
      name: "id",
      label: "ID",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "owner.username",
      label: "Owner",
      options: {
        filter: true,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const api = recurringAPIs[dataIndex];
          return api.owner.username || "Unknown";
        },
      },
    },
    {
      name: "method",
      label: "Method",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "endpoint",
      label: "Endpoint",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "next_call",
      label: "Next Call",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "payload",
      label: "Payload",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "call_delay",
      label: "Delay (days)",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "created_at",
      label: "Created at",
      options: {
        filter: true,
        sort: true,
        display: false,
        sortThirdClickReset: true,
      },
    },
    {
      name: "number_of_retries",
      label: "Number of retries",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "active",
      label: "Active",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        customBodyRender: (value) => (value ? "Yes" : "No"),
      },
    },
  ];

  const options = {
    filterType: "dropdown",
    responsive: "standard",
    selectableRows: "none",
  };

  return (
    <div>
      {RecurringAPIList ? (
        <Paper component={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                title=""
                data={recurringAPIs}
                columns={columns}
                options={options}
              />
            </ThemeProvider>
          </StyledEngineProvider>
        </Paper>
      ) : (
        <CircularProgress />
      )}
    </div>
  );
};

//   return (
//     <div className={classes.root}>
//       <List component="nav">
//         {recurringAPIs?.map((recurringAPI) => (
//           <ListItem button key={recurringAPI.id}>
//             <ListItemText
//               primary={recurringAPITitle(recurringAPI)}
//               secondary={recurringAPIInfo(recurringAPI, groups)}
//               classes={textClasses}
//             />
//             <Button
//               key={recurringAPI.id}
//               id="delete_button"
//               classes={{
//                 root: classes.recurringAPIDelete,
//                 disabled: classes.recurringAPIDeleteDisabled,
//               }}
//               onClick={() => openDialog(recurringAPI.id)}
//               disabled={!deletePermission}
//             >
//               <DeleteIcon />
//             </Button>
//             <ConfirmDeletionDialog
//               deleteFunction={deleteRecurringAPI}
//               dialogOpen={dialogOpen}
//               closeDialog={closeDialog}
//               resourceName="recurring API"
//             />
//           </ListItem>
//         ))}
//       </List>
//     </div>
//   );
// };

const RecurringAPIPage = () => {
  const { recurringAPIList } = useSelector((state) => state.recurring_apis);

  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();
  const dispatch = useDispatch();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage Recurring APIs");

  useEffect(() => {
    const getRecurringAPIs = async () => {
      await dispatch(recurringAPIsActions.fetchRecurringAPIs());
    };

    getRecurringAPIs();
  }, [dispatch]);

  if (!recurringAPIList) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Recurring APIs</Typography>
            <RecurringAPIList
              recurringAPIs={recurringAPIList}
              // deletePermission={permission}
            />
          </div>
        </Paper>
      </Grid>
      {permission && (
        <>
          <Grid item md={6} sm={12}>
            <Paper>
              <div className={classes.paperContent}>
                <Typography variant="h6">Add a New Recurring API</Typography>
                <NewRecurringAPI />
              </div>
            </Paper>
          </Grid>
        </>
      )}
    </Grid>
  );
};

RecurringAPIList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  recurringAPIs: PropTypes.arrayOf(PropTypes.any).isRequired,
  //  deletePermission: PropTypes.bool.isRequired,
};

export default RecurringAPIPage;
