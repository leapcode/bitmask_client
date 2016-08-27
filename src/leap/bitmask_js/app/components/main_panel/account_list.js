import React from 'react'
import {Button, ButtonGroup, ButtonToolbar, Glyphicon} from 'react-bootstrap'

import App from 'app'
import Account from 'models/account'

export default class AccountList extends React.Component {

  static get defaultProps() {return{
    account: null,
    accounts: [],
    onAdd: null,
    onRemove: null,
    onSelect: null
  }}

  constructor(props) {
    super(props)

    this.state = {
      mode: 'expanded'
    }

    // prebind:
    this.select = this.select.bind(this)
    this.add    = this.add.bind(this)
    this.remove = this.remove.bind(this)
    this.expand = this.expand.bind(this)
    this.collapse = this.collapse.bind(this)
  }

  select(e) {
    let account = this.props.accounts.find(
      account => account.id == e.currentTarget.dataset.id
    )
    if (this.props.onSelect) {
      this.props.onSelect(account)
    }
  }

  add() {
    App.show('wizard')
  }

  remove() {
  }

  expand() {
    this.setState({mode: 'expanded'})
  }

  collapse() {
    this.setState({mode: 'collapsed'})
  }

  render() {
    let style = {}
    let expandButton = null
    let plusminusButtons = null

    if (this.state.mode == 'expanded') {
      expandButton = (
        <Button onClick={this.collapse} className="expander btn-inverse btn-flat pull-right">
          <Glyphicon glyph="triangle-left" />
        </Button>
      )
      plusminusButtons = (
        <ButtonGroup style={style}>
          <Button onClick={this.add} className="btn-inverse">
            <Glyphicon glyph="plus" />
          </Button>
          <Button disabled={this.props.account == null} onClick={this.remove} className="btn-inverse">
            <Glyphicon glyph="minus" />
          </Button>
        </ButtonGroup>
      )
    } else {
      style.width = '60px'
      expandButton = (
        <Button onClick={this.expand} className="expander btn-inverse btn-flat pull-right">
          <Glyphicon glyph="triangle-right" />
        </Button>
      )
    }

    let items = this.props.accounts.map((account, i) => {
      let className = account == this.props.account ? 'active' : 'inactive'
      return (
        <li key={i} className={className} onClick={this.select} data-id={account.id}>
          <span className="username">{account.userpart}</span>
          <span className="domain">{account.domain}</span>
          <span className="arc top"></span>
          <span className="arc bottom"></span>
        </li>
      )
    })


    return (
      <div className="accounts" style={style}>
        <ul>
          {items}
        </ul>
        <ButtonToolbar>
          {plusminusButtons}
          {expandButton}
        </ButtonToolbar>
      </div>
    )
  }


}
