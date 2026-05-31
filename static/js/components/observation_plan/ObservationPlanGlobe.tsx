import { useState, useEffect } from "react";

import CircularProgress from "@mui/material/CircularProgress";

import { useAppDispatch } from "../../types/hooks";
import * as Actions from "../../ducks/gcnEvent";
import { GET } from "../../API";
import Button from "../Button";

import LocalizationPlot from "../localization/LocalizationPlot";

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
  // Square size (px) of the embedded skymap. Defaults to 600; the requests
  // table passes a smaller value to keep its rows compact.
  size?: number;
}

const ObservationPlanGlobe = ({
  observationplanRequest,
  retrieveLocalization = false,
  size = 600,
}: ObservationPlanGlobeProps) => {
  const dispatch = useAppDispatch();
  const displayOptions = [
    "localization",
    "sources",
    "galaxies",
    "instrument",
    "observations",
  ];
  const displayOptionsDefault: any = Object.fromEntries(
    displayOptions.map((x) => [x, false]),
  );
  displayOptionsDefault.localization = true;
  displayOptionsDefault.observations = true;
  const [obsList, setObsList] = useState<any>(null);
  const [localization, setLocalization] = useState<any>(null);
  const [selectedObservations, setSelectedObservations] = useState<any[]>([]);

  useEffect(() => {
    const fetchObsList = async () => {
      const response = (await dispatch(
        GET(
          `/api/observation_plan/${observationplanRequest.id}/geojson`,
          "skyportal/FETCH_OBSERVATION_PLAN_GEOJSON",
        ),
      )) as any;
      setObsList(response.data);
    };
    if (
      ["complete", "submitted to telescope queue"].includes(
        observationplanRequest?.status as string,
      )
    ) {
      fetchObsList();
    }
  }, [dispatch, setObsList, observationplanRequest]);

  useEffect(() => {
    const fetchLocalization = async () => {
      const response = (await dispatch(
        GET(
          `/api/localization/${observationplanRequest.localization?.dateobs}/name/${observationplanRequest.localization?.localization_name}`,
          "skyportal/FETCH_LOCALIZATION_OBSPLAN",
        ),
      )) as any;
      setLocalization(response.data);
    };
    if (retrieveLocalization) {
      fetchLocalization();
    }
  }, [dispatch, setLocalization, observationplanRequest]);

  if (!obsList) return <CircularProgress />;

  const handleDeleteObservationPlanFields = async (selectedIds: any) => {
    await dispatch(
      Actions.deleteObservationPlanFields(
        observationplanRequest.id,
        selectedIds,
      ),
    );
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        justifyItems: "center",
      }}
    >
      <LocalizationPlot
        localization={localization}
        observations={obsList}
        options={displayOptionsDefault}
        height={size}
        width={size}
        type="obsplan"
        projection="mollweide"
        selectedObservations={selectedObservations}
        setSelectedObservations={setSelectedObservations}
      />
      {obsList?.geojson?.filter((f: any) => f?.selected)?.length ? (
        <Button
          secondary
          onClick={() =>
            handleDeleteObservationPlanFields(selectedObservations)
          }
          sx={{ marginTop: "2px" }}
        >
          Delete selected fields
        </Button>
      ) : null}
    </div>
  );
};

export default ObservationPlanGlobe;
