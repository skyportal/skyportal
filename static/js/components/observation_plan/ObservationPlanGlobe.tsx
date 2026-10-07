import { lazy, Suspense, useState, useEffect } from "react";

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

import { useAppDispatch } from "../../types/hooks";
import { useDeleteObservationPlanFieldsMutation } from "../../ducks/gcnEvent";
import { useGetLocalizationQuery } from "../../ducks/localization";
import { GET } from "../../API";
import Button from "../Button";

const LocalizationPlot = lazy(() => import("../localization/LocalizationPlot"));

const PLOT_LAYERS = {
  localization: true,
  observations: true,
  sun_moon: true,
};

interface ObservationPlanRequest {
  id?: number;
  requester?: {
    id?: number;
    username?: string;
  };
  instrument?: {
    id?: number;
    name?: string;
  };
  status?: string;
  allocation?: {
    group?: {
      name?: string;
    };
  };
  localization?: {
    id?: number;
    dateobs?: string;
    localization_name?: string;
    contour?: any;
  };
}

interface ObservationPlanGlobeProps {
  observationplanRequest: ObservationPlanRequest;
  retrieveLocalization?: boolean;
  size?: number;
}

const ObservationPlanGlobe = ({
  observationplanRequest,
  retrieveLocalization = false,
  size = 600,
}: ObservationPlanGlobeProps) => {
  const dispatch = useAppDispatch();
  const [deleteObservationPlanFields] =
    useDeleteObservationPlanFieldsMutation();
  const [obsList, setObsList] = useState<any>(null);
  const [fetchFailed, setFetchFailed] = useState(false);
  const [selectedObservations, setSelectedObservations] = useState<any[]>([]);

  const { data: localization } = useGetLocalizationQuery(
    {
      dateobs: observationplanRequest.localization?.dateobs as string,
      localization_name: observationplanRequest.localization
        ?.localization_name as string,
    },
    {
      skip:
        !retrieveLocalization ||
        !observationplanRequest.localization?.dateobs ||
        !observationplanRequest.localization?.localization_name,
    },
  );

  useEffect(() => {
    let cancelled = false;
    const fetchObsList = async () => {
      const response = (await dispatch(
        GET(
          `/api/observation_plan/${observationplanRequest.id}/geojson`,
          "skyportal/FETCH_OBSERVATION_PLAN_GEOJSON",
        ),
      )) as any;
      if (cancelled) return;
      if (response?.status === "success") {
        setObsList(response.data ?? { geojson: [] });
      } else {
        setFetchFailed(true);
      }
    };
    if (
      ["complete", "submitted to telescope queue"].includes(
        observationplanRequest.status ?? "",
      )
    ) {
      fetchObsList();
    }
    return () => {
      cancelled = true;
    };
  }, [dispatch, observationplanRequest]);

  if (fetchFailed) {
    return (
      <Typography variant="body2">
        Could not load the skymap for this plan.
      </Typography>
    );
  }
  if (!obsList) return <CircularProgress />;

  return (
    <Box sx={{ display: "flex", flexDirection: "column" }}>
      <Suspense fallback={<CircularProgress />}>
        <LocalizationPlot
          localization={localization}
          observations={obsList}
          options={PLOT_LAYERS}
          height={size}
          width={size}
          projection="mollweide"
          selectedObservations={selectedObservations}
          setSelectedObservations={setSelectedObservations}
        />
      </Suspense>
      {obsList.geojson?.some((f: any) => f?.selected) && (
        <Button
          secondary
          onClick={() =>
            deleteObservationPlanFields({
              id: observationplanRequest.id as number,
              fieldIds: selectedObservations,
            })
          }
          sx={{ mt: "2px" }}
        >
          Delete selected fields
        </Button>
      )}
    </Box>
  );
};

export default ObservationPlanGlobe;
