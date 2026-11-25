import { useEffect, useState } from "react";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import { alpha } from "@mui/material/styles";

import { useUpdateSourceMutation } from "../../ducks/source";

interface WithholdFromTNSProps {
  source: {
    id: string;
    withhold_from_tns?: boolean;
    withhold_from_tns_set_at?: string | null;
    withhold_from_tns_set_by?: { username?: string } | null;
  };
  readOnly?: boolean;
}

const WithholdFromTNS = ({
  source,
  readOnly = false,
}: WithholdFromTNSProps) => {
  const [updateSource] = useUpdateSourceMutation();
  const [withheld, setWithheld] = useState(Boolean(source.withhold_from_tns));

  useEffect(() => {
    setWithheld(Boolean(source.withhold_from_tns));
  }, [source.withhold_from_tns]);

  const toggle = async () => {
    const next = !withheld;
    setWithheld(next);
    const result = await updateSource({
      id: source.id,
      payload: { withhold_from_tns: next },
    });
    if ("error" in result) setWithheld(!next);
  };

  const setBy =
    withheld && source.withhold_from_tns && source.withhold_from_tns_set_at
      ? ` (blocked by ${
          source.withhold_from_tns_set_by?.username ?? "a deleted user"
        } on ${source.withhold_from_tns_set_at.slice(0, 10)})`
      : "";

  return (
    <Tooltip
      title={
        withheld
          ? `Click to allow this source to be sent to TNS again${setBy}`
          : "Click to block this source from being sent to TNS, automatically or manually"
      }
    >
      <Chip
        size="small"
        data-testid="withhold-from-tns-button"
        aria-pressed={withheld}
        variant="outlined"
        label={withheld ? "TNS reporting off" : "TNS reporting on"}
        {...(readOnly ? {} : { onClick: toggle })}
        sx={(theme) => {
          const { error } = theme.palette;
          const red = theme.palette.mode === "dark" ? error.light : error.main;
          return {
            alignSelf: "flex-start",
            fontWeight: 500,
            borderRadius: "8px",
            ...(withheld
              ? {
                  bgcolor: alpha(red, 0.12),
                  borderColor: "transparent",
                  color: "text.primary",
                  "&&:hover": { bgcolor: alpha(red, 0.2) },
                }
              : {
                  borderStyle: "dashed",
                  color: "text.secondary",
                  "&&:hover": {
                    bgcolor: "transparent",
                    borderColor: red,
                    color: "text.primary",
                  },
                }),
          };
        }}
      />
    </Tooltip>
  );
};

export default WithholdFromTNS;
