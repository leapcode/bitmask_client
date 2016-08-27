//
// A simple list of items, with minus and plus buttons to add and remove
// items.
//

import React from 'react'
import {Button, ButtonGroup, ButtonToolbar, Glyphicon, FormControl} from 'react-bootstrap'

const CONTAINER_CSS = {
  display: "flex",
  flexDirection: "column"
}
const SELECT_CSS = {
  padding: "0px",
  flex: "1 1 1000px",
  overflowY: "scroll"
}
const OPTION_CSS = {
  padding: "10px"
}
const TOOLBAR_CSS = {
  paddingTop: "10px",
  flex: "0 0 auto"
}

class ListEdit extends React.Component {

  static get defaultProps() {return{
    width: null,
    items: [
      'aaaaaaa',
      'bbbbbbb',
      'ccccccc'
    ],
    selected: null,
    onRemove: null,
    onAdd: null,
  }}

  constructor(props) {
    super(props)
    let index = 0
    if (props.selected) {
      index = props.items.indexOf(props.selected)
    }
    this.state = {
      selected: index
    }
    this.click  = this.click.bind(this)
    this.add    = this.add.bind(this)
    this.remove = this.remove.bind(this)
  }

  setSelected(index) {
    this.setState({
      selected: index
    })
  }

  click(e) {
    let row = parseInt(e.target.value)
    if (row >= 0) {
      this.setState({selected: row})
    }
  }

  add() {
    if (this.props.onAdd) {
      this.props.onAdd()
    }
  }

  remove() {
    if (this.state.selected >= 0 && this.props.onRemove) {
      if (this.props.items.length == this.state.selected + 1) {
        // if we remove the last item, set the selected item
        // to the one right before it.
        this.setState({selected: (this.state.selected - 1)})
      }
      this.props.onRemove(this.props.items[this.state.selected])
    }
  }

  render() {
    let options = null
    if (this.props.items) {
      options = this.props.items.map((item, i) => {
        return <option style={OPTION_CSS} key={i} value={i}>{item}</option>
      }, this)
    }
    return(
      <div style={CONTAINER_CSS}>
        <FormControl
          value={this.state.selected}
          style={SELECT_CSS} className="select-list"
          componentClass="select" size="5" onChange={this.click}>
          {options}
        </FormControl>
        <ButtonToolbar className="pull-right" style={TOOLBAR_CSS}>
          <ButtonGroup>
            <Button onClick={this.add}>
              <Glyphicon glyph="plus" />
            </Button>
            <Button disabled={this.state.selected < 0} onClick={this.remove}>
              <Glyphicon glyph="minus" />
            </Button>
          </ButtonGroup>
        </ButtonToolbar>
      </div>
    )
  }

}

ListEdit.propTypes = {
  children: React.PropTypes.oneOfType([
    React.PropTypes.element,
    React.PropTypes.arrayOf(React.PropTypes.element)
  ])
}

export default ListEdit
