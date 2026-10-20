import { useState } from "react";
import Box from "@mui/material/Box";
import Pagination from "@mui/material/Pagination";

import { useGetBrokersQuery } from "../../../../ducks/brokers";
import BrokerAlertCard, {
  AlertOption,
  toAlertOption,
} from "../../../broker/BrokerAlertCard";

const PAGE_SIZE = 6;

interface FilterResultAlertsProps {
  rows: any[];
  alerts: Record<string, any>;
  brokerId: number;
  survey: string;
}

const FilterResultAlerts = ({
  rows,
  alerts,
  brokerId,
  survey,
}: FilterResultAlertsProps) => {
  const [page, setPage] = useState(1);
  const { data: brokers } = useGetBrokersQuery();
  const brokerClassname =
    brokers?.find((b) => b.id === brokerId)?.broker_classname ?? "BOOMBROKER";

  const byObject = new Map<string, AlertOption[]>();
  rows.forEach((row) => {
    const alert = alerts[String(row._id)] ?? row;
    const objectId = alert.objectId ?? row.objectId;
    if (!objectId) return;
    byObject.set(objectId, [
      ...(byObject.get(objectId) ?? []),
      toAlertOption(alert),
    ]);
  });
  const pageCount = Math.ceil(byObject.size / PAGE_SIZE);
  const current = Math.min(page, Math.max(pageCount, 1));
  const start = (current - 1) * PAGE_SIZE;

  return (
    <>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(480px, 1fr))",
          gap: 2,
        }}
      >
        {[...byObject]
          .slice(start, start + PAGE_SIZE)
          .map(([objectId, objectAlerts]) => (
            <BrokerAlertCard
              key={objectId}
              brokerId={brokerId}
              brokerClassname={brokerClassname}
              objectId={objectId}
              survey={survey}
              alerts={objectAlerts}
              lazyHistory
            />
          ))}
      </Box>
      {pageCount > 1 && (
        <Pagination
          count={pageCount}
          page={current}
          onChange={(_e, p) => setPage(p)}
          sx={{ mt: 2, display: "flex", justifyContent: "center" }}
        />
      )}
    </>
  );
};

export default FilterResultAlerts;
