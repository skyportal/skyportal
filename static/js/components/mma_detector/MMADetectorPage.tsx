import { useState } from "react";

import { useGetMMADetectorsQuery } from "../../ducks/mmadetector";
import ListPanelPage from "../ListPanelPage";
import NewMMADetector from "./NewMMADetector";
import MMADetectorEventsDialog from "./MMADetectorEventsDialog";

const MMADetectorPage = () => {
  const { data: mmadetectors = [] } = useGetMMADetectorsQuery();
  const [selected, setSelected] = useState<any>(null);

  return (
    <>
      <ListPanelPage
        name="MMADetector"
        permission="Manage allocations"
        markers={mmadetectors.map((mmadetector: any) => ({
          lat: mmadetector.lat,
          lon: mmadetector.lon,
          label: mmadetector.nickname,
        }))}
        items={mmadetectors.map((mmadetector: any) => ({
          key: `${mmadetector.id}_info`,
          title: `${mmadetector.name} (${mmadetector.nickname})`,
          lines: [
            !mmadetector.lat && !mmadetector.lon
              ? "..."
              : `Latitude: ${mmadetector.lat?.toFixed(4)} / Longitude: ${mmadetector.lon?.toFixed(4)}`,
            ...(mmadetector.elevation !== null
              ? [`Elevation: ${mmadetector.elevation}`]
              : []),
          ],
          buttonProps: {
            onClick: () => setSelected(mmadetector),
            "aria-label": `show gcn events for ${mmadetector.nickname}`,
          },
        }))}
        form={<NewMMADetector />}
      />
      {selected && (
        <MMADetectorEventsDialog
          mmadetector={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
};

export default MMADetectorPage;
