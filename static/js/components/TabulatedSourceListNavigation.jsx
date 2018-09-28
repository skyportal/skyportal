import React from 'react';
import PropTypes from 'prop-types';


class TabulatedSourceListNavigation extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      page: 1
    };

    this.handleClickPrevious = this.handleClickPrevious.bind(this);
    this.handleClickNext = this.handleClickNext.bind(this);
    this.handleClickViewAll = this.handleClickViewAll.bind(this);
  }

  handleClickPrevious(event) {
    const currentPage = this.state.page;
    this.props.getPreviousPage(currentPage);
    this.setState({ page: currentPage - 1 });
  }

  handleClickNext(event) {
    const currentPage = this.state.page;
    this.props.getNextPage(currentPage);
    this.setState({ page: currentPage + 1 });
  }

  handleClickViewAll(event) {
    // TODO: Create action to get all sources
    // What to do here??
    this.setState({ page: 0 });
  }

  render() {
    return (
      <div>
        <button type="button" onClick={this.handleClickNext}>View Next 100 Sources</button>
        &nbsp;&nbsp;
        {
          this.state.page > 1 &&
          <button type="button" onClick={this.handleClickPrevious}>View Previous 100 Sources</button>
        }
      </div>
    );
  }
}
TabulatedSourceListNavigation.propTypes = {
  getPreviousPage: PropTypes.func.isRequired,
  getNextPage: PropTypes.func.isRequired
};

export default TabulatedSourceListNavigation;
