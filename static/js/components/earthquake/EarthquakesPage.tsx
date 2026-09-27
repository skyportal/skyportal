import { Link } from "react-router-dom";

import { useGetEarthquakesQuery } from "../../ducks/earthquake";
import ListPanelPage from "../ListPanelPage";
import NewEarthquake from "./NewEarthquake";

const EarthquakesPage = () => {
  const earthquakes: any[] = useGetEarthquakesQuery().data?.events ?? [];
  const located = earthquakes.filter((earthquake) => earthquake.notices?.[0]);

  return (
    <ListPanelPage
      name="Earthquake"
      permission="Manage allocations"
      markers={located.map(({ event_id, notices: [notice] }) => ({
        lat: notice.lat,
        lon: notice.lon,
        label: event_id,
      }))}
      items={earthquakes.map(({ event_id, notices }) => {
        const notice = notices?.[0];
        return {
          key: event_id,
          title: event_id,
          lines: notice
            ? [
                `${notice.date} / Magnitude: ${notice.magnitude}`,
                `Latitude: ${notice.lat?.toFixed(4)} / Longitude: ${notice.lon?.toFixed(4)} / Depth: ${notice.depth}`,
              ]
            : [],
          buttonProps: { component: Link, to: `/earthquakes/${event_id}` },
        };
      })}
      form={<NewEarthquake />}
    />
  );
};

export default EarthquakesPage;
