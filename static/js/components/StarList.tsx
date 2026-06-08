import { useEffect, useState } from "react";

import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import IconButton from "@mui/material/IconButton";
import DownloadOutlined from "@mui/icons-material/DownloadOutlined";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import Tooltip from "@mui/material/Tooltip";
import FormControl from "@mui/material/FormControl";
import CircularProgress from "@mui/material/CircularProgress";

import { useAppDispatch } from "../types/hooks";
import { GET } from "../API";
import { useGetObservingRunQuery } from "../ducks/observingRun";

interface StarListItem {
  str: string;
}

interface StarListBodyProps {
  starList: StarListItem[] | null;
  facility: string;
  setFacility: (...args: any[]) => void;
  setStarList: (...args: any[]) => void;
}

const StarListBody = ({
  starList,
  facility,
  setFacility,
  setStarList,
}: StarListBodyProps) => {
  const handleChange = (event: any) => {
    setFacility(event.target.value);
    setStarList(null);
  };

  return (
    <div style={{ marginTop: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <FormControl size="small">
          <InputLabel id="StarListSelect">Facility</InputLabel>
          <Select
            label="Facility"
            labelId="StarListSelect"
            value={facility}
            onChange={handleChange}
            name="StarListSelectElement"
          >
            <MenuItem value="Keck">Keck</MenuItem>
            <MenuItem value="P200">P200</MenuItem>
            <MenuItem value="P200-NGPS">P200 (NGPS)</MenuItem>
            <MenuItem value="Shane">Shane</MenuItem>
          </Select>
        </FormControl>
        <div>
          <Tooltip title="Copy to clipboard">
            <span>
              <IconButton
                disabled={!starList?.length}
                onClick={() => {
                  navigator.clipboard.writeText(
                    (starList || []).map((item) => item.str).join("\n"),
                  );
                }}
              >
                <ContentCopyIcon />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Download">
            <span>
              <IconButton
                disabled={!starList?.length}
                onClick={() => {
                  const element = document.createElement("a");
                  const file = new Blob(
                    [(starList || []).map((item) => item.str).join("\n")],
                    { type: "text/plain" },
                  );
                  element.href = URL.createObjectURL(file);
                  element.download = `starlist_${facility.toLowerCase()}${
                    facility === "P200-NGPS" ? ".csv" : ".txt"
                  }`;
                  document.body.appendChild(element);
                  element.click();
                }}
              >
                <DownloadOutlined />
              </IconButton>
            </span>
          </Tooltip>
        </div>
      </div>
      {starList === null ? (
        <CircularProgress sx={{ mt: 1 }} size={32} />
      ) : (
        <pre
          style={{
            fontSize: "0.75rem",
            border: "solid lightgray 1px",
            background: "#eee",
            padding: "1em",
            borderRadius: "0.5em",
            overflowX: "scroll",
          }}
        >
          {starList.map((item) => item.str).join("\n")}
        </pre>
      )}
    </div>
  );
};

interface StarListProps {
  sourceId: string;
}

const StarList = ({ sourceId }: StarListProps) => {
  const [starList, setStarList] = useState<StarListItem[] | null>(null);
  const dispatch = useAppDispatch();
  const [facility, setFacility] = useState("Keck");

  useEffect(() => {
    const fetchStarList = async () => {
      const response: any = await dispatch(
        GET(
          `/api/sources/${sourceId}/offsets?facility=${facility}`,
          "skyportal/FETCH_STARLIST",
        ),
      );

      let data = response.data.starlist_info || [];
      // if the facility is P200-NGPS, we add the header to the starlist
      if (facility === "P200-NGPS") {
        data = [
          {
            str: "NAME,RA,DECL,OFFSET_RA,OFFSET_DEC,COMMENT,PRIORITY,BINSPAT,BINSPECT,SLITANGLE,SLITWIDTH,AIRMASS_MAX,WRANGE_LOW,WRANGE_HIGH,CHANNEL,MAGNITUDE,MAGFILTER,EXPTIME,NEXP",
          },
          ...data,
        ];
      }
      setStarList(data);
    };

    fetchStarList();
  }, [sourceId, dispatch, facility]);

  return (
    <StarListBody
      starList={starList}
      facility={facility}
      setFacility={setFacility}
      setStarList={setStarList}
    />
  );
};

export const ObservingRunStarList = ({
  observingRunId,
}: {
  observingRunId?: number | string;
}) => {
  const dispatch = useAppDispatch();
  const [starList, setStarList] = useState<StarListItem[] | null>(null);
  const { data: observingRun } = useGetObservingRunQuery(
    observingRunId as number | string,
    { skip: observingRunId == null },
  ) as { data: any };
  const assignments = observingRun?.assignments ?? [];
  const [facility, setFacility] = useState("Keck");

  useEffect(() => {
    const fetchStarList = async () => {
      const promises = assignments.map((assignment: any) =>
        dispatch(
          GET(
            `/api/sources/${assignment.obj_id}/offsets?facility=${facility}&observing_run_id=${assignment.run_id}`,
            "skyportal/FETCH_STARLIST",
          ),
        ),
      );
      const standard_promise = [
        dispatch(
          GET(
            `/api/internal/standards?facility=${facility}`,
            "skyportal/FETCH_STANDARDS",
          ),
        ),
      ];
      const starlistInfo: StarListItem[] = [];
      const values: any[] = await Promise.allSettled(promises);
      const standard_value: any[] = await Promise.allSettled(standard_promise);
      values.push(standard_value[0]);

      values.forEach((response) =>
        starlistInfo.push(...response.value.data.starlist_info),
      );

      // if the facility is P200-NGPS, we add the header to the starlist
      if (facility === "P200-NGPS") {
        starlistInfo.unshift({
          str: "NAME,RA,DECL,OFFSET_RA,OFFSET_DEC,COMMENT,PRIORITY,BINSPAT,BINSPECT,SLITANGLE,SLITWIDTH,AIRMASS_MAX,WRANGE_LOW,WRANGE_HIGH,CHANNEL,MAGNITUDE,MAGFILTER,EXPTIME,NEXP",
        });
      }

      setStarList(starlistInfo);
    };
    if (assignments.length > 0) {
      fetchStarList();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, facility, observingRun?.id, assignments.length]);
  return (
    <StarListBody
      starList={starList}
      facility={facility}
      setStarList={setStarList}
      setFacility={setFacility}
    />
  );
};

export default StarList;
