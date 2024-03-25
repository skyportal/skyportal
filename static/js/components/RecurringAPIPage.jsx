import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import makeStyles from "@mui/styles/makeStyles";
// import { showNotification } from "baselayer/components/Notifications";
// import CircularProgress from "@mui/material/CircularProgress";
import MUIDataTable from "mui-datatables";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";

import { DialogContent, Dialog, DialogTitle } from "@mui/material";
import NewRecurringAPI from "./NewRecurringAPI";

import * as recurringAPIsActions from "../ducks/recurring_apis";

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

// export function recurringAPITitle(recurringAPI) {
//   if (!recurringAPI?.endpoint) {
//     return (
//       <div>
//         <CircularProgress color="secondary" />
//       </div>
//     );
//   }

//   const result = `${recurringAPI?.endpoint} / ${recurringAPI?.method}`;

//   return result;
// }

// export function recurringAPIInfo(recurringAPI) {
//   if (!recurringAPI?.next_call) {
//     return (
//       <div>
//         <CircularProgress color="secondary" />
//       </div>
//     );
//   }

//   const result = `Next call: ${recurringAPI.next_call} / Delay [days]: ${recurringAPI.call_delay} / Active: ${recurringAPI.active}`;

//   return result;
// }

// const RecurringAPIList = ({ recurringAPIs, options }) => {
// const dispatch = useDispatch();
// const classes = useStyles();
// const theme = useTheme();

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

//   return (
//     <div>
//       <MUIDataTable
//         title=""
//         data={recurringAPIs}
//         columns={columns}
//         options={options}
//       />
//     </div>
//   );
// };

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
  const [openNewForm, setOpenNewForm] = useState(false);

  console.log("recurringAPIs");
  console.log(recurringAPIList);

  // const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();
  const dispatch = useDispatch();

  // const permission =
  //   currentUser.permissions?.includes("System admin") ||
  //   currentUser.permissions?.includes("Manage Recurring APIs");

  useEffect(() => {
    const getRecurringAPIs = async () => {
      await dispatch(recurringAPIsActions.fetchRecurringAPIs());
    };

    getRecurringAPIs();
  }, [dispatch]);

  // if (!recurringAPIs) {
  //   return (
  //     <div>
  //       <CircularProgress color="secondary" />
  //     </div>
  //   );
  // }

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
          const api = recurringAPIList[dataIndex];
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
        customBodyRenderLite: (dataIndex) => {
          const api = recurringAPIList[dataIndex];
          return JSON.stringify(api.payload) || "Unknown";
        },
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
    customToolbar: () => (
      <IconButton
        name="new_recurring_api_form"
        onClick={() => {
          setOpenNewForm(true);
        }}
      >
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div className={classes.paperContent}>
      <MUIDataTable
        title="Recurring APIs"
        data={recurringAPIList}
        columns={columns}
        options={options}
      />
      <Dialog
        open={openNewForm}
        onClose={() => {
          setOpenNewForm(false);
        }}
        aria-labelledby="form-dialog-title"
      >
        <DialogTitle id="form-dialog-title">
          Add a New Recurring API
        </DialogTitle>
        <DialogContent>
          <NewRecurringAPI />
        </DialogContent>
      </Dialog>
    </div>
  );
};

//   return (
//     <Grid container spacing={3}>
//       <Grid item md={6} sm={12}>
//         <Paper elevation={1}>
//           <div className={classes.paperContent}>
//             <Typography variant="h6">List of Recurring APIs</Typography>
//             <RecurringAPIList
//               recurringAPIs={recurringAPIList}
//               // deletePermission={permission}
//             />
//           </div>
//         </Paper>
//       </Grid>
//       {permission && (
//         <>
//           <Grid item md={6} sm={12}>
//             <Paper>
//               <div className={classes.paperContent}>
//                 <Typography variant="h6">Add a New Recurring API</Typography>
//                 <NewRecurringAPI />
//               </div>
//             </Paper>
//           </Grid>
//         </>
//       )}
//     </Grid>
//   );
// };

// RecurringAPIList.propTypes = {
//   // eslint-disable-next-line react/forbid-prop-types
//   recurringAPIs: PropTypes.arrayOf(PropTypes.any).isRequired,
//   //  deletePermission: PropTypes.bool.isRequired,
// };

export default RecurringAPIPage;
