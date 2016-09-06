import React from 'react'
//import { Button, Glyphicon, Alert } from 'react-bootstrap'
import SectionLayout from './section_layout'
import Account from 'models/account'
import Spinner from 'components/spinner'
import bitmask from 'lib/bitmask'

export default class EmailSection extends React.Component {

  static get defaultProps() {return{
    account: null
  }}

  constructor(props) {
    super(props)
    this.state = {
      status: null
    }
    this.openKeys  = this.openKeys.bind(this)
    this.openApp   = this.openApp.bind(this)
    this.openPrefs = this.openPrefs.bind(this)

    console.log('email constructor')
  }

  openKeys() {}
  openApp() {}
  openPrefs() {}

  render () {
    //let message = null
    //if (this.state.error) {
    //  // style may be: success, warning, danger, info
    //  message = (
    //    <Alert bsStyle="danger">{this.state.error}</Alert>
    //  )
    //}
    let button = null
    if (this.state.status == 'ready') {
      button = <Button onClick={this.openApp}>Open Email</Button>
    }
    return (
      <SectionLayout icon="envelope" status="on" button={button}>
        <h1>inbox: </h1>
      </SectionLayout>
    )
  }
}
