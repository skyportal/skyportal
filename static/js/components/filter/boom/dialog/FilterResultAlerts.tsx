import { useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Pagination from "@mui/material/Pagination";
import Skeleton from "@mui/material/Skeleton";

import {
  useGetBrokerAlertsQuery,
  useGetBrokersQuery,
} from "../../../../ducks/brokers";
import BrokerAlertCard, {
  toAlertOption,
} from "../../../broker/BrokerAlertCard";
import { CutoutsSkeleton } from "../../../broker/CutoutTriplet";

const PAGE_SIZE = 6;

interface ResultCardProps {
  brokerId: number;
  brokerClassname: string;
  objectId: string;
  survey: string;
  passingCandid: string | number | undefined;
}

const ResultCard = ({
  brokerId,
  brokerClassname,
  objectId,
  survey,
  passingCandid,
}: ResultCardProps) => {
  const { data, isLoading } = useGetBrokerAlertsQuery({
    brokerId,
    params: { objectId, survey },
  });

  if (isLoading) {
    return (
      <Card variant="outlined" sx={{ p: 2 }}>
        <Skeleton width="40%" height={28} />
        <Skeleton width="60%" />
        <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
          <CutoutsSkeleton size="5rem" />
          <Skeleton variant="rounded" height="10rem" sx={{ flex: 1 }} />
        </Box>
      </Card>
    );
  }

  const alerts = Array.isArray(data) ? data.map(toAlertOption) : [];
  return (
    <BrokerAlertCard
      brokerId={brokerId}
      brokerClassname={brokerClassname}
      objectId={objectId}
      survey={survey}
      alerts={alerts.length ? alerts : [{ candid: passingCandid as any }]}
      initialCandid={passingCandid}
    />
  );
};

interface FilterResultAlertsProps {
  rows: any[];
  brokerId: number;
  survey: string;
}

const FilterResultAlerts = ({
  rows,
  brokerId,
  survey,
}: FilterResultAlertsProps) => {
  const [page, setPage] = useState(1);
  const { data: brokers } = useGetBrokersQuery();
  const brokerClassname =
    brokers?.find((b) => b.id === brokerId)?.broker_classname ?? "BOOMBROKER";

  const passingCandids = new Map<string, string | number | undefined>();
  rows.forEach((row) => {
    const objectId = row?.objectId ?? row?.candidate?.objectId;
    if (objectId && !passingCandids.has(objectId)) {
      passingCandids.set(objectId, toAlertOption(row).candid);
    }
  });
  const objects = [...passingCandids];
  const pageCount = Math.ceil(objects.length / PAGE_SIZE);
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
        {objects
          .slice(start, start + PAGE_SIZE)
          .map(([objectId, passingCandid]) => (
            <ResultCard
              key={objectId}
              brokerId={brokerId}
              brokerClassname={brokerClassname}
              objectId={objectId}
              survey={survey}
              passingCandid={passingCandid}
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
