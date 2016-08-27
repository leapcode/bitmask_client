//
// A modal popup to add a new provider.
//

import React from 'react'
import { FormGroup, ControlLabel, FormControl, HelpBlock, Button, Modal } from 'react-bootstrap'
import Spinner from '../spinner'
import Validate from '../../lib/validate'
import App from '../../app'

class AddProviderModal extends React.Component {

  static get defaultProps() {return{
    title: 'Add a provider',
    onClose: null
  }}

  constructor(props) {
    super(props)
    this.state = {
      validationState: null,
      errorMsg: null,
      domain: ""
    }
    this.accept   = this.accept.bind(this)
    this.cancel   = this.cancel.bind(this)
    this.changed  = this.changed.bind(this)
  }

  accept() {
    if (this.state.domain) {
      App.providers.add(this.state.domain)
    }
    this.props.onClose()
  }

  cancel() {
    this.props.onClose()
  }

  changed(e) {
    let domain = e.target.value
    let newState = null
    let newMsg   = null

    if (domain.length > 0) {
      let error = Validate.domain(domain)
      newState = error ? 'error' : 'success'
      newMsg   = error
    }
    this.setState({
      domain: domain,
      validationState: newState,
      errorMsg: newMsg
    })
  }

  render() {
    let help = null
    if (this.state.errorMsg) {
      help = <HelpBlock>{this.state.errorMsg}</HelpBlock>
    } else {
      help = <HelpBlock>&nbsp;</HelpBlock>
    }
    let form = <form onSubmit={this.accept} autoComplete="off">
      <FormGroup controlId="addprovider" validationState={this.state.validationState}>
        <ControlLabel>Domain</ControlLabel>
        <FormControl
          type="text"
          ref="domain"
          autoFocus
          value={this.state.domain}
          onChange={this.changed}
          onBlur={this.changed} />
        <FormControl.Feedback/>
        {help}
      </FormGroup>
      <Button onClick={this.accept}>Add</Button>
    </form>

    return(
      <Modal show={true} onHide={this.cancel}>
        <Modal.Header closeButton>
          <Modal.Title>{this.props.title}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {form}
        </Modal.Body>
      </Modal>
    )
  }
}

export default AddProviderModal