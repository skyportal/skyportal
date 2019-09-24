import React from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';

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
      <table>
        <tbody>
          <tr>
            <td>
              <b>
                Value
              </b>&nbsp;&nbsp;
            </td>
            <td>
              <b>
                Name
              </b>&nbsp;&nbsp;
            </td>
            <td>
              <b>
                ACLS
              </b>&nbsp;&nbsp;
            </td>
            <td>
              <b>
                Created
              </b>&nbsp;&nbsp;
            </td>
            <td>
              <b>
                Delete
              </b>
            </td>
          </tr>
          {
            tokens.map((token) => (
              <tr key={token.id}>
                <td>
                  <input type="text" id={token.id} value={token.id} readOnly />
                  <button type="button" onClick={() => copyToken(token.id)}>
                    Copy to Clipboard
                  </button>
                </td>
                <td>
                  {token.name}
                </td>
                <td>
                  {token.acls.join(', ')}
                </td>
                <td>
                  {token.created_at}
                </td>
                <td>
                  <a href="#top" onClick={() => deleteToken(token.id)}>
                    Delete
                  </a>
                </td>
              </tr>
            ))
          }
        </tbody>
      </table>
    </div>
  );
};
TokenList.propTypes = {
  tokens: PropTypes.arrayOf(PropTypes.object).isRequired
};

export default TokenList;
