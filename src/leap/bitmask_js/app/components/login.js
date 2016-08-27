import React from 'react'
import ReactDOM from 'react-dom'

import { FormGroup, ControlLabel, FormControl, HelpBlock, Button,
  Checkbox, Glyphicon, Overlay, Tooltip, Alert } from 'react-bootstrap'
import Spinner from './spinner'

import Validate from 'lib/validate'
import App from 'app'
import Account from 'models/account'

class Login extends React.Component {

  static get defaultProps() {return{
    rememberAllowed: false,   // if set, show remember password checkbox
    domain: null,             // if set, only allow this domain
    onLogin: null
  }}

  constructor(props) {
    super(props)

    // validation states can be null, 'success', 'warning', or 'error'

    this.state = {
      loading: false,

      authError: false,     // authentication error message

      username: null,
      usernameState: null,  // username validation state
      usernameError: false, // username help message

      password: null,
      passwordState: null,  // password validation state
      passwordError: false, // password help message

      disabled: false,
      remember: false       // remember is checked?
    }

    // prebind:
    this.onUsernameChange = this.onUsernameChange.bind(this)
    this.onUsernameBlur   = this.onUsernameBlur.bind(this)
    this.onPassword = this.onPassword.bind(this)
    this.onSubmit   = this.onSubmit.bind(this)
    this.onRemember = this.onRemember.bind(this)
  }

  componentDidMount() {
    Validate.loadPasswdLib()
  }

  render () {
    let rememberCheck = ""
    let submitButton  = ""
    let usernameHelp  = null
    let passwordHelp  = null
    let message = null

    if (this.props.rememberAllowed) {
      let props = {
        style: {marginTop: "0px"},
        onChange: this.onRemember
      }

      if (this.state.remember) {
        rememberCheck = <Checkbox {...props} checked>
          Remember username and password
        </Checkbox>
      } else {
        rememberCheck = <Checkbox {...props}>
          Remember username and password
        </Checkbox>
      }
    }

    if (this.state.authError) {
      // style may be: success, warning, danger, info
      message = (
        <Alert bsStyle="danger">{this.state.authError}</Alert>
      )
    }

    if (this.state.usernameError) {
      usernameHelp = <HelpBlock>{this.state.usernameError}</HelpBlock>
      // let props = {shouldUpdatePosition: true, show:true, placement:"right",
      //              target:this.refs.username}
      // usernameHelp = (
      //   <Overlay {...props}>
      //     <Tooltip id="username-tooltip">{this.state.usernameError}</Tooltip>
      //   </Overlay>
      // )
    } else {
      //usernameHelp = <HelpBlock>&nbsp;</HelpBlock>
    }

    if (this.state.passwordError) {
      passwordHelp = <HelpBlock>{this.state.passwordError}</HelpBlock>
      // let props = {shouldUpdatePosition: true, show:true, placement:"right",
      //              target:this.refs.password, component: {this}}
      // passwordHelp = (
      //   <Overlay {...props}>
      //     <Tooltip id="password-tooltip">{this.state.passwordError}</Tooltip>
      //   </Overlay>
      // )
    } else {
      //passwordHelp = <HelpBlock>&nbsp;</HelpBlock>
    }

    let buttonProps = {
      type: "button",
      onClick: this.onSubmit,
      disabled: !this.maySubmit()
    }
    if (this.state.loading) {
       submitButton = <Button block {...buttonProps}><Spinner /></Button>
    } else {
       submitButton = <Button block {...buttonProps}>Log In</Button>
    }

    let usernameref = null
    if (this.props.domain) {
      usernameref = function(c) {
        if (c != null) {
          let textarea = ReactDOM.findDOMNode(c)
          let start = textarea.value.indexOf('@')
          if (textarea.selectionStart > start) {
            textarea.setSelectionRange(start, start)
          }
        }
      }
    }

    let form = <form onSubmit={this.onSubmit}>
      {message}
      <FormGroup style={{marginBottom: '10px' }} controlId="loginUsername" validationState={this.state.usernameState}>
        <ControlLabel>Username</ControlLabel>
        <FormControl
          componentClass="textarea"
          style={{resize: "none"}}
          rows="1"
          ref={usernameref}
          autoFocus
          value={this.state.username}
          onChange={this.onUsernameChange}
          onBlur={this.onUsernameBlur} />
        {this.state.usernameState == 'success' ? null : <FormControl.Feedback/>}
        {usernameHelp}
      </FormGroup>

      <FormGroup controlId="loginPassword" validationState={this.state.passwordState}>
        <ControlLabel>Password</ControlLabel>
        <FormControl
          type="password"
          ref="password"
          value={this.state.password}
          onChange={this.onPassword} />
        {this.state.passwordState == 'success' ? null : <FormControl.Feedback/>}
        {passwordHelp}
      </FormGroup>

      {submitButton}
      {rememberCheck}
    </form>

    return form
  }

  //
  // Here we do a partial validation, because the user has not stopped typing.
  //
  onUsernameChange(e) {
    let username = e.target.value.toLowerCase().replace("\n", "")
    if (this.props.domain) {
      let [userpart, domainpart] = username.split(
        new RegExp('@|' + this.props.domain.replace(".", "\\.") + '$')
      )
      username = [userpart, this.props.domain].join('@')
    }
    let error = Validate.usernameInteractive(username, this.props.domain)
    let state = null
    if (error) {
      state = 'error'
    } else {
      if (username && username.length > 0) {
        let finalError = Validate.username(username)
        state = finalError ? null : 'success'
      }
    }
    this.setState({
      username: username,
      usernameState: state,
      usernameError: error ? error : null
    })
  }

  //
  // Here we do a more complete validation, since the user have left the field.
  //
  onUsernameBlur(e) {
    let username = e.target.value.toLowerCase()
    this.setState({
      username: username
    })
    if (username.length > 0) {
      this.validateUsername(username)
    } else {
      this.setState({
        usernameState: null,
        usernameError: null
      })
    }
  }

  onPassword(e) {
    let password = e.target.value
    this.setState({password: password})
    if (password.length > 0) {
      this.validatePassword(password)
    } else {
      this.setState({
        passwordState: null,
        passwordError: null
      })
    }
  }

  onRemember(e) {
    let currentValue = e.target.value == 'on' ? true : false
    let value = !currentValue
    this.setState({remember: value})
  }

  validateUsername(username) {
    let error = Validate.username(username, this.props.domain)
    this.setState({
      usernameState: error ? 'error' : 'success',
      usernameError: error ? error : null
    })
  }

  validatePassword(password) {
    let state = null
    let message = null
    let result = Validate.passwordStrength(password)
    if (result) {
      message = "Time to crack: " + result.crack_times_display.offline_slow_hashing_1e4_per_second
      if (result.score == 0) {
        state = 'error'
      } else if (result.score == 1 || result.score == 2) {
        state = 'warning'
      } else {
        state = 'success'
      }
    }
    this.setState({
      passwordState: state,
      passwordError: message
    })
  }

  maySubmit() {
    return(
      !this.stateLoading &&
      !this.state.usernameError &&
      this.state.username != "" &&
      this.state.password != ""
    )
  }

  onSubmit(e) {
    e.preventDefault() // don't reload the page please!
    if (!this.maySubmit()) { return }
    this.setState({loading: true})

    let account = new Account(this.state.username)
    account.login(this.state.password).then(
      account => {
        this.setState({loading: false})
        if (this.props.onLogin) {
          this.props.onLogin(account)
        }
      },
      error => {
        console.log(error)
        if (error == "") {
          error = 'Something failed, but we did not get a message'
        }
        this.setState({
          loading: false,
          usernameState: 'error',
          passwordState: 'error',
          authError: error
        })
      }
    )
  }

}

export default Login