import bitmask from 'lib/bitmask'
import Account from 'models/account'

class Application {
  constructor() {
  }

  //
  // main entry point for the application
  //
  start() {
    Account.active().then(account => {
      if (account == null) {
        this.show('greeter', {onLogin: this.onLogin.bind(this)})
      } else {
        this.show('main', {initialAccount: account})
      }
    }, error => {
      this.show('error', {error: error})
    })
  }

  onLogin(account) {
    this.show('main', {initialAccount: account})
  }

  show(panel, properties) {
    this.switcher.show(panel, properties)
  }
}

var App = new Application
export default App