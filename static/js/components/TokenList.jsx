import React from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';

import Button from '@material-ui/core/Button';
import TextField from '@material-ui/core/TextField';
import Paper from '@material-ui/core/Paper';
import Table from '@material-ui/core/Table';
import TableHead from '@material-ui/core/TableHead';
import TableBody from '@material-ui/core/TableBody';
import TableRow from '@material-ui/core/TableRow';
import TableCell from '@material-ui/core/TableCell';

import * as Action from '../ducks/profile';


const copyToken = (elementID) => {
  const el = document.getElementById(elementID);
  el.select();
  document.execCommand("copy");
};

const TokenList = ({ tokens }) => {
  const dispatch = useDispatch();
  if (!tokens) {
    return <div />;
  }

  const deleteToken = (token_id) => {
    dispatch(Action.deleteToken(token_id));
  };

  return (
    <div>
      <h3>
        My Tokens
      </h3>
      <Table size="small" component={Paper}>
        <TableHead>
          <TableRow>
            <TableCell>Value</TableCell>
            <TableCell />
            <TableCell>Name</TableCell>
            <TableCell>ACLS</TableCell>
            <TableCell>Created</TableCell>
            <TableCell>Delete</TableCell>
          </TableRow>
        </TableHead>

        <TableBody>
          {
            tokens.map((token) => (
              <TableRow key={token.id}>
                <TableCell>
                  <TextField id={token.id} value={token.id} readOnly={1} />
                </TableCell>
                <TableCell>
                  <Button
                    variant="contained"
                    size="small"
                    onClick={() => copyToken(token.id)}
                  >
                    Copy to Clipboard
                  </Button>
                </TableCell>
                <TableCell>
                  {token.name}
                </TableCell>
                <TableCell>
                  {token.acls.join(', ')}
                </TableCell>
                <TableCell>
                  {token.created_at}
                </TableCell>
                <TableCell>
                  <a href="#top" onClick={() => deleteToken(token.id)}>
                    Delete
                  </a>
                </TableCell>
              </TableRow>
            ))
          }
        </TableBody>
      </Table>
    </div>
  );
};
TokenList.propTypes = {
  tokens: PropTypes.arrayOf(PropTypes.object).isRequired
};

export default TokenList;
