import React from 'react';
import PropTypes from 'prop-types';


class SearchBox extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      sourceID: "",
      ra: "",
      dec: "",
      radius: "",
      startDate: "",
      endDate: "",
      simbadClass: "",
      hasTNSname: false
    };

    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleReset = this.handleReset.bind(this);
    this.handleInputChange = this.handleInputChange.bind(this);
    this.handleClickNextPage = this.handleClickNextPage.bind(this);
    this.handleClickPreviousPage = this.handleClickPreviousPage.bind(this);
  }

  handleInputChange(event) {
    const newState = {};
    newState[event.target.name] = event.target.type === 'checkbox' ?
                                  event.target.checked : event.target.value;
    this.setState(newState);
  }

  handleSubmit(event) {
    event.preventDefault();
    this.props.filterSources(this.state);
  }

  handleReset(event) {
    this.setState({
      sourceID: "",
      ra: "",
      dec: "",
      radius: "",
      startDate: "",
      endDate: "",
      simbadClass: "",
      hasTNSname: false
    });
    this.props.fetchSources();
  }

  handleClickNextPage(event) {
    event.preventDefault();
    this.props.nextPage(this.state);
  }

  handleClickPreviousPage(event) {
    event.preventDefault();
    this.props.previousPage(this.state);
  }

  render() {
    return (
      <div>
        <h4>Filter Sources</h4>
        <form id="sourceFilterForm" onSubmit={this.handleSubmit}>
          <table>
            <tbody>
              <tr>
                <td colSpan="3">
                  <label><b>By Name/ID  </b></label>
                </td>
              </tr>
              <tr>
                <td colSpan="3">
                  <label>Source ID/Name (can be substring):  </label>
                  <input
                    type="text"
                    name="sourceID"
                    value={this.state.sourceID}
                    onChange={this.handleInputChange}
                    size="6"
                  />
                </td>
              </tr>
              <tr>
                <td colSpan="3">
                  <label><b>By Position  </b></label>
                </td>
              </tr>
              <tr>
                <td>
                  <label>RA (degrees):  </label>
                  <input
                    type="text"
                    name="ra"
                    value={this.state.ra}
                    onChange={this.handleInputChange}
                    size="6"
                  />
                </td>
                <td>
                  <label>Dec (degrees):  </label>
                  <input
                    type="text"
                    name="dec"
                    value={this.state.dec}
                    onChange={this.handleInputChange}
                    size="6"
                  />
                </td>
                <td>
                  <label>Radius (degrees):  </label>
                  <input
                    type="text"
                    name="radius"
                    value={this.state.radius}
                    onChange={this.handleInputChange}
                    size="6"
                  />
                </td>
              </tr>
              <tr>
                <td colSpan="3">
                  <label><b>By Time Last Detected </b></label>
                </td>
              </tr>
              <tr>
                <td colSpan="3">
                  Required format: %Y-%m-%dT%H:%M:%S in UTC time, e.g. 2012-08-30T00:00:00
                </td>
              </tr>
              <tr>
                <td>
                  <label>Start Date:  </label>
                  <input
                    type="text"
                    name="startDate"
                    value={this.state.startDate}
                    onChange={this.handleInputChange}
                    size="6"
                  />
                </td>
                <td>
                  <label>End Date:  </label>
                  <input
                    type="text"
                    name="endDate"
                    value={this.state.endDate}
                    onChange={this.handleInputChange}
                    size="6"
                  />
                </td>
              </tr>
              <tr>
                <td>
                  <label><b>By Simbad Class  </b></label>
                </td>
              </tr>
              <tr>
                <td>
                  <label>Class:  </label>
                  <input
                    type="text"
                    name="simbadClass"
                    value={this.state.simbadClass}
                    onChange={this.handleInputChange}
                    size="6"
                  />
                </td>
              </tr>
              <tr>
                <td>
                  <label><b>Must Have TNS Name: </b></label>
                  <input
                    type="checkbox"
                    name="hasTNSname"
                    checked={this.state.hasTNSname}
                    onChange={this.handleInputChange}
                    size="6"
                  />
                </td>
              </tr>
              <tr>
                <td>
                  <input type="submit" id="sourceFilterFormSubmitButton" disabled={this.props.sources.queryInProgress} />
                </td>
                <td>
                  <button type="button" onClick={this.handleReset}>Reset</button>
                </td>
              </tr>
            </tbody>
          </table>
          <br />
          {
            this.props.sources &&
            <div>
              <div style={{ display: "inline-block" }}>
                <button
                  type="button"
                  onClick={this.handleClickPreviousPage}
                  disabled={this.props.sources.pageNumber == 1}
                >
                  View Previous 100 Sources
                </button>
              </div>
              <div style={{ display: "inline-block" }}>
                <i>
                  Displaying {this.props.sources.sourceNumberingStart}-
                  {this.props.sources.sourceNumberingEnd} of&nbsp;
                  {this.props.sources.totalMatches} matching sources.
                </i>
              </div>
              <div style={{ display: "inline-block" }}>
                <button
                  type="button"
                  onClick={this.handleClickNextPage}
                  disabled={this.props.sources.lastPage}
                >
                  View Next 100 Sources
                </button>
              </div>
            </div>
          }
        </form>
        <br />
      </div>
    );
  }
}
SearchBox.propTypes = {
  sources: PropTypes.object.isRequired,
  filterSources: PropTypes.func.isRequired,
  fetchSources: PropTypes.func.isRequired,
  nextPage: PropTypes.func.isRequired,
  previousPage: PropTypes.func.isRequired
};

export default SearchBox;
