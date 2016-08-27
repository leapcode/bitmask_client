import React from 'react'
import { Button, Glyphicon, Alert } from 'react-bootstrap'
import SectionLayout from './section_layout'
import Login from 'components/login'
import Spinner from 'components/spinner'
import Account from 'models/account'

import bitmask from 'lib/bitmask'

export default class UserSection extends React.Component {

  static get defaultProps() {return{
    account: null,
    onLogout: null,
    onLogin: null
  }}

  constructor(props) {
    super(props)
    this.state = {
      error: null,
      loading: false
    }
    this.logout = this.logout.bind(this)
  }

  logout() {
    this.setState({loading: true})
    this.props.account.logout().then(
      account => {
        this.setState({error: null, loading: false})
        if (this.props.onLogout) {
          this.props.onLogout(account)
        }
      }, error => {
        this.setState({error: error, loading: false})
      }
    )
  }

  render () {
    let message = null
    if (this.state.error) {
      // style may be: success, warning, danger, info
      message = (
        <Alert bsStyle="danger">{this.state.error}</Alert>
      )
    }

    if (this.props.account.authenticated) {
      let button = null
      if (this.state.loading) {
        button = <Button disabled={true}><Spinner /></Button>
      } else {
        button = <Button onClick={this.logout}>Log Out</Button>
      }
      return (
        <SectionLayout icon="user" buttons={button} status="on">
          <h1>{this.props.account.address}</h1>
          {message}
        </SectionLayout>
      )
    } else {
      return (
        <SectionLayout icon="user" className="wide-margin">
          <Login onLogin={this.props.onLogin} domain={this.props.account.domain} />
        </SectionLayout>
      )
    }
  }
}
