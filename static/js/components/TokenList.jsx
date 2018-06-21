import React from 'react';


const TokenList = (props) => {
  if (!props.tokens) {
    return <div></div>;
  }

  return (
    <div>
      <h3>My Tokens</h3>
      <table>
        <tbody>
          <tr>
            <td>
              <b>Value</b>&nbsp;&nbsp;
            </td>
            <td>
              <b>Description</b>&nbsp;&nbsp;
            </td>
            <td>
              <b>ACLS</b>&nbsp;&nbsp;
            </td>
            <td>
              <b>Created</b>&nbsp;&nbsp;
            </td>
            <td>
              <b>Delete</b>
            </td>
          </tr>
          {
            props.tokens.map(token => (
              <tr>
                <td>
                  <input type="text" id={token.id} value={token.id} readOnly />&nbsp;
              <button onClick={() => copyToken(token.id)}>Copy to Clipboard</button>&nbsp;&nbsp;
                </td>
                <td>
                  {token.description}&nbsp;&nbsp;
                </td>
                <td>
                  {token.acls.join(', ')}&nbsp;&nbsp;
                </td>
                <td>
                  {token.created_at}&nbsp;&nbsp;
                </td>
                <td>
                  <a href="#" onClick={() => props.deleteToken(token.id)}>Delete</a>
                </td>
              </tr>
            ))
          }
        </tbody>
      </table>
    </div>
  );
};

const copyToken = (elementID) => {
  const el = document.getElementById(elementID);
  console.log(elementID);
  el.select();
  document.execCommand("copy");
};

export default TokenList;
