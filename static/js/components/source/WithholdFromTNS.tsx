import { useEffect, useState } from "react";
import Tooltip from "@mui/material/Tooltip";
import { alpha, type Theme } from "@mui/material/styles";

import Button from "../Button";
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
        readOnly
          ? `This source ${withheld ? "is never" : "can be"} sent to TNS${setBy}`
          : withheld
            ? `Click to allow this source to be sent to TNS again${setBy}`
            : "Click to block this source from being sent to TNS, automatically or manually"
      }
    >
      <span>
        <Button
          size="small"
          data-testid="withhold-from-tns-button"
          aria-pressed={withheld}
          disabled={readOnly}
          onClick={toggle}
          sx={(theme: Theme) => {
            const { error } = theme.palette;
            const red =
              theme.palette.mode === "dark" ? error.light : error.main;
            return {
              py: "3px",
              border: "1px solid",
              "&&.Mui-disabled": { color: "text.secondary" },
              ...(withheld
                ? {
                    borderColor: red,
                    color: "text.primary",
                    "&&:hover": { bgcolor: alpha(red, 0.08) },
                  }
                : {
                    borderStyle: "dashed",
                    borderColor: "divider",
                    color: "text.secondary",
                    "&&:hover": {
                      bgcolor: "transparent",
                      borderColor: red,
                      color: "text.primary",
                    },
                  }),
            };
          }}
        >
          {withheld ? "TNS reporting off" : "TNS reporting on"}
        </Button>
      </span>
    </Tooltip>
  );
};

export default WithholdFromTNS;
