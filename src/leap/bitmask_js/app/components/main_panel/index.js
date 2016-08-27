//
// The main panel manages the current account and the list of available accounts
//
// It displays multiple sections, one for each service.
//

import React from 'react'
import App from 'app'
import Login from 'components/login'

import './main_panel.less'
import AccountList from './account_list'
import UserSection from './user_section'

export default class MainPanel extends React.Component {

  static get defaultProps() {return{
    initialAccount: null
  }}

  constructor(props) {
    super(props)
    this.state = {
      account: null,
      accounts: []
    }
    this.activateAccount = this.activateAccount.bind(this)
  }

  componentWillMount() {
    if (this.props.initialAccount) {
      this.setState({
        account: this.props.initialAccount,
        accounts: [this.props.initialAccount]
      })
    }
  }

  activateAccount(account) {
    this.setState({
      account: account,
      accounts: [account]
    })
  }

  render() {
    return (
      <div className="main-panel">
        <AccountList account={this.state.account} accounts={this.state.accounts} onSelect={this.activateAccount} />
        <div className="body">
          <UserSection account={this.state.account} onLogin={this.activateAccount} onLogout={this.activateAccount}/>
        </div>
      </div>
    )
  }

}
