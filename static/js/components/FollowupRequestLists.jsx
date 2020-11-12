import React from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import { makeStyles } from "@material-ui/core/styles";

import * as Actions from "../ducks/source";

import EditFollowupRequestDialog from "./EditFollowupRequestDialog";

const useStyles = makeStyles(() => ({
  followupRequestTable: {
    borderSpacing: "0.7em",
  },
}));

const FollowupRequestLists = ({
  followupRequests,
  instrumentList,
  instrumentFormParams,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const deleteRequest = (id) => {
    dispatch(Actions.deleteFollowupRequest(id));
  };

  if (
    instrumentList.length === 0 ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <p>No robotic followup requests for this source...</p>;
  }

  const instLookUp = instrumentList.reduce((r, a) => {
    r[a.id] = a;
    return r;
  }, {});

  const requestsGroupedByInstId = followupRequests.reduce((r, a) => {
    r[a.allocation.instrument.id] = [
      ...(r[a.allocation.instrument.id] || []),
      a,
    ];
    return r;
  }, {});

  Object.values(requestsGroupedByInstId).forEach((value) => {
    value.sort();
  });

  return (
    <div>
      {Object.keys(requestsGroupedByInstId).map((instrument_id) => {
        // get the flat, unique list of all keys across all requests
        const keys = requestsGroupedByInstId[instrument_id].reduce((r, a) => {
          Object.keys(a.payload).forEach((key) => {
            if (!r.includes(key)) {
              r = [...r, key];
            }
          });
          return r;
        }, []);

        const implementsDelete =
          instrumentFormParams[instrument_id].methodsImplemented.delete;
        const implementsEdit =
          instrumentFormParams[instrument_id].methodsImplemented.update;
        const modifiable = implementsEdit || implementsDelete;

        return (
          <div key={`instrument_${instrument_id}_table_div`}>
            <h3>{instLookUp[instrument_id].name} Requests</h3>
            <table
              className={classes.followupRequestTable}
              data-testid={`followupRequestTable_${instrument_id}`}
            >
              <thead>
                <td>Requester</td>
                <td>Allocation</td>
                {keys.map((key) => (
                  <td key={key}>
                    {Object.keys(
                      instrumentFormParams[instrument_id].aliasLookup
                    ).includes(key)
                      ? instrumentFormParams[instrument_id].aliasLookup[key]
                      : key}
                  </td>
                ))}
                <td>Status</td>
                {modifiable && <td>Modify</td>}
              </thead>
              <tbody>
                {requestsGroupedByInstId[instrument_id].map(
                  (followupRequest) => (
                    <tr key={followupRequest.id}>
                      <td>{followupRequest.requester.username}</td>
                      <td>{followupRequest.allocation.group.name}</td>
                      {keys.map((key) => (
                        <td key={`fr_${followupRequest.id}_${key}`}>
                          {Array.isArray(followupRequest.payload[key])
                            ? followupRequest.payload[key].join(",")
                            : followupRequest.payload[key]}
                        </td>
                      ))}
                      <td>{followupRequest.status}</td>
                      {modifiable && (
                        <td>
                          {implementsDelete && (
                            <button
                              type="button"
                              name={`deleteRequest_${followupRequest.id}`}
                              onClick={() => {
                                deleteRequest(followupRequest.id);
                              }}
                            >
                              Delete
                            </button>
                          )}
                          {implementsEdit && (
                            <EditFollowupRequestDialog
                              followupRequest={followupRequest}
                              instrumentFormParams={instrumentFormParams}
                            />
                          )}
                        </td>
                      )}
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
};

FollowupRequestLists.propTypes = {
  followupRequests: PropTypes.arrayOf(
    PropTypes.shape({
      requester: PropTypes.shape({
        id: PropTypes.number,
        username: PropTypes.string,
      }),
      instrument: PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
      }),
      status: PropTypes.string,
      allocation: PropTypes.shape({
        group: PropTypes.shape({
          name: PropTypes.string,
        }),
      }),
    })
  ).isRequired,
  instrumentList: PropTypes.arrayOf(
    PropTypes.shape({
      band: PropTypes.string,
      created_at: PropTypes.string,
      id: PropTypes.number,
      name: PropTypes.string,
      type: PropTypes.string,
      telescope_id: PropTypes.number,
    })
  ).isRequired,
  instrumentFormParams: PropTypes.shape({
    formSchema: PropTypes.objectOf(PropTypes.any),
    uiSchema: PropTypes.objectOf(PropTypes.any),
    methodsImplemented: PropTypes.objectOf(PropTypes.any),
    aliasLookup: PropTypes.objectOf(PropTypes.any),
  }).isRequired,
};

export default FollowupRequestLists;
