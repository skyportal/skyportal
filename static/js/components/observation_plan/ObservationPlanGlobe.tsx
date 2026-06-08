import { useState, useEffect } from "react";

import CircularProgress from "@mui/material/CircularProgress";

import { useAppDispatch } from "../../types/hooks";
import { useDeleteObservationPlanFieldsMutation } from "../../ducks/gcnEvent";
import { useGetLocalizationQuery } from "../../ducks/localization";
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

  if (!obsList) return <CircularProgress />;

  const handleDeleteObservationPlanFields = async (selectedIds: any) => {
    await deleteObservationPlanFields({
      id: observationplanRequest.id as number,
      fieldIds: selectedIds,
    });
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
