import React, { lazy, Suspense, useState } from "react";
import { useSelector } from "react-redux";
import Grid from "@mui/material/Grid";
import Button from "../Button";
import NewMMADetector from "./NewMMADetector";
import MMADetectorList from "./MMADetectorList";
import Paper from "../Paper";
import Spinner from "../Spinner";
import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import Typography from "@mui/material/Typography";
// lazy import the MMADetectorMap component
const MMADetectorMap = lazy(() => import("./MMADetectorMap"));

const panelStyles = (isSelected) => ({
  color: "text.secondary",
  width: "50%",
  transition: "background-color 0.3s ease",
  boxShadow: "0 -4px 8px -4px rgba(0, 0, 0, 0.2)",
  borderBottomRightRadius: 0,
  borderBottomLeftRadius: 0,
  "&:hover": {
    boxShadow: isSelected
      ? "0 -4px 8px -4px rgba(0, 0, 0, 0.2)"
      : "0 -3px 8px -5px rgba(0, 0, 0, 0.2)",
    backgroundColor: isSelected ? "#f0f2f5" : "#e0e0e0",
  },
  ...(isSelected && {
    zIndex: 3,
    backgroundColor: "#f0f2f5",
    borderBottom: "none",
  }),
});

const MMADetectorPage = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("lg"));
  const currentUser = useSelector((state) => state.profile);
  const canManage = currentUser.permissions?.includes("Manage allocations");
  const { mmadetectorList } = useSelector((state) => state.mmadetectors);
  const [newMMADetector, setNewMMADetector] = useState(false);

  return (
    <Suspense fallback={<Spinner />}>
      <Grid container spacing={3}>
        <Grid item lg={8} md={6} sm={12}>
          <Paper>
            {isMobile ? (
              <>
                <Typography variant="h6" sx={{ fontWeight: "500" }}>
                  List of MMADetectors
                </Typography>
                <MMADetectorList isMobile />
              </>
            ) : (
              <MMADetectorMap mmadetectors={mmadetectorList} />
            )}
          </Paper>
        </Grid>
        {(!isMobile || canManage) && (
          <Grid item lg={4} md={6} sm={12}>
            {!isMobile && canManage && (
              <Box>
                <Button
                  secondary
                  onClick={() => setNewMMADetector(false)}
                  sx={panelStyles(!newMMADetector)}
                >
                  MMADetectors
                </Button>
                <Button
                  secondary
                  onClick={() => setNewMMADetector(true)}
                  sx={panelStyles(newMMADetector)}
                >
                  <AddIcon />
                </Button>
              </Box>
            )}
            <Paper>
              {isMobile && (
                <Typography variant="h6" sx={{ fontWeight: "500" }}>
                  Add a New MMADetector
                </Typography>
              )}
              {canManage && (newMMADetector || isMobile) ? (
                <NewMMADetector /> // Display it when user can manage and newMMADetector is true or on mobile
              ) : (
                <MMADetectorList /> // Display this list when isMobile is false or user cannot manage or newMMADetector is false
              )}
            </Paper>
          </Grid>
        )}
      </Grid>
    </Suspense>
  );
};

export default MMADetectorPage;
